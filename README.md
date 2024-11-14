# 1. 说明
这是基于开源的 FunASR 实现的说话人分离的 GUI 项目，可以在支持图形界面中的任意 PC 端运行 \
要求 python version >= 3.8
# 2. 安装
执行下面命令来安装依赖
```shell
pip install -U funasr modelscope ffmpeg-python
```
此外还需要安装 torch，可以到 torch 官方中根据自己电脑情况安装不同版本的 torch \
安装 ffmpeg，可以到 github 中搜索 ffmpeg，下载解压后，配置环境变量 \
# 3. 功能
支持对指定的单个或者多个音频中不同的说话人讲的话进行分离，分别归类到不同的目录中 \
如果你需要对视频进行切片，需要修改源代码，欢迎有能力的大佬提交 Pr
# 4. 其它
模型中的模型可以到 https://modelscope.cn 下载 \
用到的模型有下面这些：
```shell
speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
speech_fsmn_vad_zh-cn-16k-common-pytorch
punc_ct-transformer_zh-cn-common-vocab272727-pytorch
speech_campplus_sv_zh-cn_16k-common
```
下载后保存在电脑的家目录的 .cache/modelscope/hub/iic/ 目录中
# 5. 联系
可以添加语音识别和语音合成交流群 905555036 \
个人技术分享博客1：https://lukeewin.top \
个人技术分享博客2：https://blog.lukeewin.top
