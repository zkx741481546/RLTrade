from stable_baselines import *
from TradeEnv import TradeEnv
import seaborn as sns
import matplotlib.pyplot as plt
from Config import *
stock_code = ['000938_XSHE', '601318_XSHG', '601628_XSHG', '002049_XSHE', '000001_XSHE']




file_list = os.listdir('./checkpoints/' + net_type)
max_index = -1
max_file_name = ''
for filename in file_list:
    index = int(filename.split("_")[2])
    if index > max_index:
        max_index = index
        max_file_name = filename
# max_file_name = 'rl_model_24006656_steps.zip'
model_path = './checkpoints/' + net_type + '/' + max_file_name
# model_path = "./BestModels/" + net_type + "/" + "best_model.zip"
print(model_path)
model = TRPO.load(model_path, policy_kwargs=policy_args)
mode = 'test'

env = TradeEnv(obs_time_size='60 day', obs_delta_frequency='1 day', sim_delta_time='1 day',
               start_episode=0, episode_len=EP_LEN, stock_codes=stock_code,
               result_path="E:/运行结果/TRPO/" + FILE_TAG + "/" + mode + "/",
               stock_data_path='./Data/test/',
               poundage_rate=1.5e-3, reward_verbose=1, post_processor=post_processor, end_index_bound=-10, principal=1e6,
               agent_state=False)
env.seed(0)
env = env.unwrapped
env.result_path = "E:/运行结果/TRPO/" + FILE_TAG + "/" + mode + "/"
profit = []
base = []
ep = 0
while ep < 100:
    print(ep)
    s = env.reset()
    flag = False
    for step in range(250):
        a, _ = model.predict(s)
        s, r, done, _ = env.step(a)
        if done or s is None or r is None:
            flag = True
            break
    env.render("manual")
    if not flag:
        his = np.array(env.trade_history)
        profit_list = np.squeeze(
            (his[:, 4].astype(np.float32) + his[:, 1].astype(np.float32) * his[:, 3].astype(
                np.float32) - env.principal) / env.principal).tolist()
        price_list = np.array(np.squeeze(his[:, 1]))
        price_list = ((price_list - price_list[0]) / price_list[0]).astype(np.float32).tolist()
        profit.append(profit_list)
        base.append(price_list)
        ep += 1
# seborn绘图
plt.close('all')
ax = plt.subplot(1, 1, 1)
ax.set_title('TRPO')
ax.set_xlabel('Episode')
ax.set_ylabel('Moving averaged episode averaged profit')
profit = np.array(profit)
base = np.array(base)
sns.tsplot(data=profit, time=np.arange(0, profit.shape[1]), ax=ax, color='r')
sns.tsplot(data=base, time=np.arange(0, base.shape[1]), ax=ax, color='b')
try:
    plt.savefig(net_type + '_' + max_file_name + '.png')
except:
    print('reward图片被占用，无法写入')
