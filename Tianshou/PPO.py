import sys

if sys.platform == 'win32':
    sys.path.append("D:\\PycharmProjects\\Stable-BaselineTrading\\")
else:
    sys.path.append("/usr/zkx/Stable-BaselineTrading/")
import tianshou as ts
from Env.TradeEnv import TradeEnv
from Tianshou.Net.MultiStockTradeNet import *
from torch.utils.tensorboard import SummaryWriter
from Tianshou.StockReplayBuffer import *
import json
import argparse
import os


def make_env(i, env_type, test_mode):
    return lambda: TradeEnv(**config['env'][env_type], env_id=i, run_id=run_id, config=config, test_mode=test_mode)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--config', type=str)
    argparser.add_argument('--test', action='store_true', default=False)
    argparser.add_argument('--load_dir', type=str, default=None)
    argparser.add_argument('--resume', type=str, default=None)
    args = argparser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    save_dir = args.load_dir if args.load_dir is not None and args.test else config['train']['save_dir']
    run_id = None
    if config['global_wandb'] and not args.test:
        import wandb

        if args.resume is None:
            wandb.init(**config['wandb'], config=config)
        else:
            wandb.init(**config['wandb'], config=config, resume=args.resume)
        if save_dir is None:
            save_dir = wandb.run.dir + "\\" + "policy.pth"
        run_id = wandb.run.id
    if not args.test:
        train_envs = ts.env.SubprocVectorEnv(
            [make_env(i, 'train', args.test) for i in range(config['env']['train_env_num'])],
            wait_num=config['env']['wait_num'], timeout=config['env']['time_out'])
    else:
        config['env']['test']['result_path'] = 'E:/运行结果/TD3/test_with_trained_model/'
        config['env']['test']['wandb_log'] = False
        config['env']['test']['auto_open_result'] = True
    test_envs = ts.env.SubprocVectorEnv(
        [make_env(i, 'test', args.test) for i in range(config['env']['test_env_num'])],
        wait_num=config['env']['wait_num'], timeout=config['env']['time_out'])

    state_space = test_envs.observation_space[0]
    action_shape = test_envs.action_space[0].shape

    actor_net = StockDistributionalActor(state_space, action_shape, config['env']['train']['agent_state'], config['train']['gpu'], **config['policy']['actor'])
    critic_net = StockCritic(state_space, action_shape, config['env']['train']['agent_state'], config['train']['gpu'], **config['policy']['critic'])
    optim = torch.optim.Adam(list(actor_net.parameters()) + list(critic_net.parameters()), lr=config['policy']['lr'], weight_decay=config['policy']['l2_ratio'])

    if config['train']['gpu']:
        actor_net = actor_net.cuda()
        critic_net = critic_net.cuda()
    if args.test:
        actor_net = actor_net.eval()
        critic_net = critic_net.eval()
    config['policy']['policy_parameter']['dist_fn'] = get_module(config['policy']['policy_parameter']['dist_fn'])
    policy = ts.policy.PPOPolicy(actor_net, critic_net, optim,
                                 **config['policy']['policy_parameter'],
                                 action_range=(
                                     test_envs.action_space[0].low.mean(), test_envs.action_space[0].high.mean()))
    if not args.test:
        train_collector = ts.data.Collector(policy, train_envs,
                                            StockPrioritizedReplayBuffer(**config['train']['replay_buffer'],
                                                                         **config['env']['train']))
    elif args.test or args.resume is not None:
        policy.load_state_dict(torch.load(save_dir))
        print('模型读取完毕')

    test_collector = ts.data.Collector(policy, test_envs)

    if not args.test:
        writer = SummaryWriter(config['train']['log_dir'])
        result = ts.trainer.onpolicy_trainer(policy, train_collector, test_collector,
                                             **config['train']['train_parameter'],
                                             writer=writer,
                                             save_fn=lambda p: torch.save(p.state_dict(), save_dir))
        torch.save(policy.state_dict(), save_dir)
    else:
        ts.trainer.test_episode(policy, test_collector, epoch=0, n_episode=1, test_fn=None)
