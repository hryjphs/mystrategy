# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 11:18:04 2019

@author: Rui
"""

import talib as ta
import numpy as np
import pandas as pd

"""
将策略需要用到的信号生成器抽离出来
"""

class rSignal():

    def __init__(self):
        self.author = 'Rui'

    def maEnvironment(self, am, paraDict):
        """
        条件一：短期均线（5，10，20均线）要多头排列，趋势往上：ma(c,5)>=ma(c,10) and ma(c,10)>=ma(c,20) and ma(c,5)>ref(ma(c,5),1) and ma(c,10)>ref(ma(c,10),1) and ma(c,20)>ref(ma(c,20),1)
        条件二：5日均线上涨速率大于103或10日均线上涨速率大于102:MA(C,5)/REF(MA(C,5),1)>1.03 OR MA(C,10)/REF(MA(C,10),1)>1.02
        """
        fastPeriod = paraDict["fastPeriod"]
        mediumPeriod = paraDict["mediumPeriod"]
        slowPeriod = paraDict["slowPeriod"]

        fma = ta.MA(am.close, fastPeriod)
        mma = ta.MA(am.close, mediumPeriod)
        lma = ta.MA(am.close, slowPeriod)
        maup1 = fma[-1]>fma[-2] and mma[-1]>mma[-2] and lma[-1]>lma[-2] and fma[-1]>mma[-1] and mma[-1]>lma[-1]
        maup2 = fma[-1]>fma[-2] *1.03 and mma[-1]>mma[-2]*1.02
        
        envDirection = 0 
        if maup1 and maup2:
            envDirection = 1 
        return envDirection, fma, mma, lma

    def zhangtingSignal(self,am,paraDict):
        """
        条件一：先一天涨停：REF(C,1)/REF(C,2)>1.099
        条件二：先一天涨停的成交量是他前一天成交量的0.5-3倍，不可过大量：REF(HSCOL,1)/REF(HSCOL,2)<3 AND REF(HSCOL,1)/REF(HSCOL,2)>0.5
        条件三：先一天涨停板要自然涨停，而且不能是烂板，不能尾盘涨停，不能是一字板（先一天涨停比较坚决）,close>open
        """
        zt1 = am.close[-1]>am.close[-2]*1.099
        zt2 = am.volume[-1]>am.volume[-2]*0.5 and am.volume[-1]<am.volume[-2]*3
        zt3 = am.close[-1]>am.open[-1]
        
        zhangtingSignal = 0
        if zt1 and zt2 and zt3:
            zhangtingSignal = 1
        return zhangtingSignal
    
    def ExitSignal(self, am, paraDict):
        """
        利用布林轨道计算出场信号
        情况一exitTrendSignal1：跌进30分钟41ma布林轨道，开始出场
        情况二exitTrendSignal2：跌破布林轨道日线中轨，考虑完全减仓
        """
        
        upper, middle, lower = ta.BBANDS(am.close, matype=ta.MA_Type.T3)
        exitTrendSignal1 = am.close[-1]<upper[-1] and  am.close[-1]>middle[-1] and am.close[-2]>upper[-2]
        exitTrendSignal2 =  am.close[-1]<middle[-1] and am.close[-2]>middle[-2]
        return exitTrendSignal1, exitTrendSignal2, upper, middle, lower
 
    