# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 11:51:47 2019

@author: Administrator
"""

"""
这里的Demo是一个最简单的双均线策略实现
"""

from __future__ import division
from vnpy.trader.vtConstant import *
from vnpy.trader.app.ctaStrategy import CtaTemplate
import talib as ta
import numpy as np
from datetime import datetime
from signal import rSignal


########################################################################
# 策略继承CtaTemplate
class rStrategy(CtaTemplate):
    className = 'rStrategy'
    author = 'Rui'
    
    # 策略变量
    transactionPrice = {} # 记录成交价格
    
     # 参数列表
    paramList = [
                 'symbolList', 'barPeriod', 'lot',
                 'timeframeMap',
                 'envPeriod',
                 "fastPeriod","mediumPeriod","slowPeriod",
                 "stoplossPct"
                ]    
    
    # 变量列表
    varList = ['transactionPrice']  
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['posDict', 'eveningDict']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        # 首先找到策略的父类（就是类CtaTemplate），然后把DoubleMaStrategy的对象转换为类CtaTemplate的对象
        super().__init__(ctaEngine, setting)
        self.paraDict = setting
        self.symbol = self.symbolList[0]      #在setting里面定义了数值
        self.transactionPrice = None # 生成成交价格的字典
        self.trendStatus = None
        #self.nPos = 0

        self.chartLog = {
                'datetime':[],
                'upper':[],
                'middle':[],
                'lower':[],
                'slowMa':[],
                'mediumMa':[],
                'fastMa':[],
                }

    def prepare_data(self):
        for timeframe in list(set(self.timeframeMap.values())):
            self.registerOnBar(self.symbol, timeframe, None)

    def arrayPrepared(self, period):
        am = self.getArrayManager(self.symbol, period)
        if not am.inited:
            return False, None
        else:
            return True, am

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略"""
        self.setArrayManagerSize(self.barPeriod)
        self.prepare_data()
        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略启动')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略"""
        self.writeCtaLog(u'策略停止')
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送"""
        pass
    #----------------------------------------------------------------------
   def stoploss(self, bar):
        """止损"""
        if self.posDict[self.symbol+'_LONG']>0:
            if bar.low<self.transactionPrice*(1-self.stoplossPct):
                self.cancelAll()
                self.sell(self.symbol, bar.close*0.99, self.posDict[self.symbol+'_LONG'])
        if self.posDict[self.symbol+'_SHORT']>0:
            if bar.high>self.transactionPrice*(1+self.stoplossPct):
                self.cancelAll()
                self.cover(self.symbol, bar.close*1.01, self.posDict[self.symbol+'_SHORT'])
 
    def on5MinBar(self, bar):
        self.strategy(bar)

    def strategy(self, bar):
        
        signalPeriod= self.timeframeMap["signalPeriod"]
        envPeriod= self.timeframeMap["envPeriod"]
        
        # 根据出场信号出场
        exitSig = self.exitSignal(signalPeriod)
        self.exitOrder(bar, exitSig)

        # 根据进场信号进场
        entrySig = self.entrySignal(envPeriod, signalPeriod)
        self.entryOrder(bar, entrySig)

        # 触发止损
        if exitSig == 0:
            self.stoploss(bar)

       
    def exitSignal(self, signalPeriod):
        arrayPrepared, amSignal = self.arrayPrepared(signalPeriod)
        algorithm = rSignal()
        exitsignal = 0
        if arrayPrepared:
            exitTrendSignal1, exitTrendSignal2, upper, middle, lower = algorithm.ExitSignal(amSignal, self.paraDict)
            if exitTrendSignal1 == 1:
                exitsignal = 1
            else if exitTrendSignal2 == 1:
                exitsignal = 2
                
            self.chartLog['upper'].append(upper[-1])
            self.chartLog['middle'].append(middle[-1])
            self.chartLog['lower'].append(lower[-1])
        
        return exitsignal
    
  
    def exitOrder(self, bar, exitSig):
        if self.posDict[self.symbol+'_LONG']>0:
            if exitSig==1 :
                self.cancelAll()
                self.sell(self.symbol, bar.close*0.99, (self.posDict[self.symbol+'_LONG'])/3)
            if exitSig==2 :
                self.cancelAll()
                self.sell(self.symbol, bar.close*0.99, self.posDict[self.symbol+'_LONG'])
        

    def entrySignal(self, envPeriod, signalPeriod):
        # 1 才entry
        arrayPrepared1, amEnv = self.arrayPrepared(envPeriod)
        arrayPrepared2, amSignal = self.arrayPrepared(signalPeriod)
        entrySignal = 0
        if arrayPrepared1 and arrayPrepared2:
            algorithm = rSignal()
            envDirection, fma, mma, lma = algorithm.maEnvironment(amEnv, self.paraDict)
            zhangtingSignal = algorithm.zhangtingSignal(amSignal, self.paraDict)
            
            if envDirection==1 and zhangtingSignal==1:
                entrySignal = 1
            

            self.chartLog['datetime'].append(datetime.strptime(amSignal.datetime[-1], "%Y%m%d %H:%M:%S"))
            self.chartLog['mediumMa'].append(mma[-1])
            self.chartLog['fastMa'].append(fma[-1])
            self.chartLog['slowMa'].append(sma[-1])
        return entrySignal


    def entryOrder(self, bar, entrySignal):
        # 如果进场时手头没有多头持仓
        if (entrySignal==1) and (self.posDict[self.symbol+'_LONG']==0):
            # 如果没有空头持仓，则直接做多
            if  self.posDict[self.symbol+'_SHORT']==0:
                self.buy(self.symbol, bar.close*1.01, self.lot)  # 成交价*1.01发送高价位的限价单，以最优市价买入进场
            # 如果有空头持仓，则先平空，再做多
            elif self.posDict[self.symbol+'_SHORT'] > 0:
                self.cancelAll() # 撤销挂单
                self.cover(self.symbol, bar.close*1.01, self.posDict[self.symbol+'_SHORT']) 
                self.buy(self.symbol, bar.close*1.01, self.lot)
        # 发出状态更新事件
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送"""
        if order.offset == OFFSET_OPEN:  # 判断成交订单类型
            self.transactionPrice = order.price_avg # 记录成交价格
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送"""
        pass
    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass