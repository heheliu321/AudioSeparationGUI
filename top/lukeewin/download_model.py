# !/usr/bin/env python
# _*_ coding utf-8 _*_
# @Time: 2025/1/4 17:05
# @Author: Luke Ewin
# @Blog: https://blog.lukeewin.top
from modelscope import snapshot_download
snapshot_download('iic/speech_campplus_sv_zh-cn_16k-common')
snapshot_download('iic/speech_fsmn_vad_zh-cn-16k-common-pytorch')
snapshot_download('iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch')
snapshot_download('iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch')
