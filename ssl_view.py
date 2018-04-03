# encoding: UTF-8
'''
基差分析
作者:王文科 当前版本v1.0 日期 201801
'''
import seaborn as sns
sns.set(style="darkgrid",palette="muted",color_codes=True)
import re 
import matplotlib.pyplot as plt
import matplotlib.dates as mdate
import os 
import datetime as dt
import pandas as pd 
import numpy as np
from WindPy import w 
w.start()


class ssl:
    def __init__(self,cn1,cn2,cr1,cr2,yr,iscnt=True,mode='rto'):
        #品种基本信息
        self.cmtinfo=pd.read_csv('cmdt_info.csv',index_col=0) 
        self.cmt1=self.cnt_to_cmt(cn1).upper()
        self.cmt2=self.cnt_to_cmt(cn2).upper()
        if iscnt==True:
            cnt1=cn1+'M.'+self.cmtinfo.loc[self.cmt1]['exchange']
            cnt2=cn2+'M.'+self.cmtinfo.loc[self.cmt2]['exchange']
        else:
            cnt1=cn1
            cnt2=cn2
        #参数mode表示价差(spd)或者比价(rto),默认为比价
        self.mode=mode
        #输入两个合约代码,一般为商品历史同月合约
        self.cnt1=cnt1
        self.cnt2=cnt2 
        self.coef1=int(cr1)
        self.coef2=int(cr2)
        #设置画图的label
        self.label_1=cn1
        self.label_2=cn2
        x='' if self.coef1==1 else str(self.coef1)+'*'
        y='' if self.coef2==1 else str(self.coef2)+'*'
        self.label_3=self.label_1+' / '+self.label_2 if mode=='rto' else x+self.label_1+' - '+y+self.label_2
        #价格模式，默认为收盘价 
        self.pricemode='close'
        #数据观测起始期，默认为2010年
        self.start=yr+'-1-1'

        if iscnt==True: #如果iscnt=False,表示不是正常期货合约
            #获取交割月份
            self.iscnt=True
            self.settm1=re.sub("\D", "",self.cnt1)
            try:
                self.settm2=re.sub("\D", "",self.cnt2)  #输入为正套结构
            except:
                self.settm2=self.settm1  # 如果cnt2不是合约,而是指数等，那么交割月等同合约1 
        else:
            self.iscnt=False
        
        self.bar=self.bar().copy()

    def cnt_to_cmt(self,cnt):
        try:
            if cnt[1].isdigit():
                cmt=cnt[0]
            else:
                cmt=cnt[:2]
        except:
            cmt=cnt
        return cmt
         
    def daily_bar(self):
        #日度数据获取
        wd=w.wsd([self.cnt1,self.cnt2],self.pricemode,self.start,"")
        data=np.array(wd.Data).T
        times=map(lambda x:pd.to_datetime(x).date(),wd.Times)
        return pd.DataFrame(data, index=times, columns=['cnt1','cnt2'])
    
            
    def rtdprice(self):
        #实时价格获取
        wd=w.wsq([self.cnt1,self.cnt2],"rt_latest")
        ti=dt.datetime.now()
        if ti.hour>20:
            Times=pd.to_datetime(wd.Times[0]).date()+dt.timedelta(days=1)
        else:
            Times=pd.to_datetime(wd.Times[0]).date()
        return pd.DataFrame(np.array(wd.Data[0]), columns=[Times], index=['cnt1','cnt2']).T

    def bar(self):
        ti=dt.datetime.now()
        # 用实时价格来替代最新交易日的价格
        if ti.hour>20:
            bar=self.daily_bar().copy().append(self.rtdprice().copy())
        else:
            bar=self.daily_bar().copy()
            rtdbar=self.rtdprice().copy()
            bar.loc[rtdbar.index[-1]] = rtdbar.iloc[-1]
        bar.dropna(inplace=True)
        if self.mode=='rto':
            bar[self.mode]=self.coef1*bar['cnt1']*1.0/(self.coef2*bar['cnt2'])
        else:
            bar[self.mode]=self.coef1*bar['cnt1']-self.coef2*bar['cnt2']
        return bar 

    def annualized(self):
        df=self.bar
        lastdate=str(self.bar.index[-1].month)+'-'+str(self.bar.index[-1].day) #最新日期
        if self.iscnt==True:
            #合约存续期(issueday-settleday),剔除交割月份
            issueday='{}'+'-'+('01' if int(self.settm2)==12 else str(int(self.settm2)+1))+'-1'
            settleday='{}'+'-'+self.settm1+'-1'
            #生成基础时间序列,用于数据填充,月份的先后排列很重要
            setyear=2016
            if self.cmt1 !=self.cmt2:   #跨品种套利
                if int(self.settm1)<=int(self.settm2):
                    issueday='{}'+'-'+('01' if int(self.settm2)==12 else str(int(self.settm2)+1))+'-1'
                    settleday='{}'+'-'+self.settm1+'-1'
                    setnextyr=setyear if int(self.settm2)==12 else setyear+1
                else: 
                    issueday='{}'+'-'+('01' if int(self.settm1)==12 else str(int(self.settm2)+1))+'-1'
                    settleday='{}'+'-'+self.settm2+'-1'
                    setnextyr=setyear if int(self.settm1)==12 else setyear+1
            else:   #跨期套利
                if int(self.settm1)<=int(self.settm2): #正套结构
                    issueday='{}'+'-'+('01' if int(self.settm2)==12 else str(int(self.settm2)+1))+'-1'
                    settleday='{}'+'-'+self.settm1+'-1'
                    setnextyr=setyear if int(self.settm2)==12 else setyear+1
                else:                                  #反套结构
                    issueday='{}'+'-'+('01' if int(self.settm1)==12 else str(int(self.settm2)+1))+'-1'
                    settleday='{}'+'-'+self.settm2+'-1'
                    setnextyr=setyear if int(self.settm1)==12 else setyear+1

            #日历日序列
            wd=w.tdays(issueday.format(setyear),settleday.format(setnextyr),"Days=Alldays")
            

            calendar=wd.Data[0][:-1]
            calendar_days=[str(i.month)+'-'+str(i.day) for i in calendar]      #转成m-d的形式,用于merge数据的index
            self.currentday=calendar_days.index(lastdate)                      #定位合约周期中最新日期位于的天数位置
            data=pd.DataFrame(calendar_days,index=calendar,columns=['id'])
            data.reset_index(inplace=True)
            dic={'cnt1':data.copy(),'cnt2':data.copy(),self.mode:data.copy()}
            for yr in range(df.index[0].year,df.index[-1].year+1):
                start=pd.to_datetime(issueday.format(yr)).date()
                end=pd.to_datetime(settleday.format(yr+(setnextyr-setyear))).date()
                if start>df.index[-1] or end<df.index[0]:
                    continue
                else:
                    for item in ['cnt1','cnt2',self.mode]:
                        temp=df[df.index.map(lambda x:x>=start and x<end)][[item]]
                        temp.rename(columns={item:yr},inplace=True) 
                        temp['id']=map(lambda x:str(x.month)+'-'+str(x.day),temp.index)
                        dic[item]=pd.merge(dic[item],temp,on='id',how='left')
        else:
            #生成基础时间序列,用于数据填充
            issueday='{}-01-01'
            settleday='{}-01-01'
            #日历日序列
            wd=w.tdays(issueday.format(2016),settleday.format(2017),"Days=Alldays") 
            calendar=wd.Data[0][:-1]
            calendar_days=[str(i.month)+'-'+str(i.day) for i in calendar] #转成m-d的形式,用于merge数据的index
            self.currentday=calendar_days.index(lastdate)  
            data=pd.DataFrame(calendar_days,index=calendar,columns=['id'])
            data.reset_index(inplace=True)
            dic={'cnt1':data.copy(),'cnt2':data.copy(),self.mode:data.copy()}
            for yr in range(df.index[0].year,df.index[-1].year+1):
                start=pd.to_datetime(issueday.format(yr)).date()     
                end=pd.to_datetime(settleday.format(yr+1)).date()  
                if start>df.index[-1] or end<df.index[0]:
                    continue
                else:
                    for item in ['cnt1','cnt2',self.mode]:
                        temp=df[df.index.map(lambda x:x>=start and x<end)][[item]]
                        temp.rename(columns={item:yr},inplace=True) 
                        temp['id']=map(lambda x:str(x.month)+'-'+str(x.day),temp.index)
                        dic[item]=pd.merge(dic[item],temp,on='id',how='left') 
        return dic


    def plot(self):
        dic=self.annualized()
        #画季节性图,一共3幅,(比价或价差,合约1,合约2)
        #fig,axes=plt.subplots(3,1)
        ax=0
        legendtitle=iter([self.label_3,self.label_1,self.label_2])
        fig=plt.figure(figsize=(12, 12)) 
        #fig.tight_layout()
        for item in [self.mode,'cnt1','cnt2']:
            if ax==0:
                axes=plt.subplot(2,1,1)
            else:
                axes=plt.subplot(2,2,ax+2)
            df=dic[item]
            del df['id']
            df.set_index('index',inplace=True)                #将index换成日期
            df.interpolate(inplace=True,method='time')        #线性插值填补非交易日的数据
            colors=iter(['royalblue','steelblue','teal','sage','olive','orange','coral','brown','mediumorchid','pink','grey'])   #设置画图颜色
            cols=list(df.columns)
            count=0
                
            for i in cols:     #如果想从最近合约开始画,用cols[::-1],逆序循环
                if count>10:         #做多画10个合约
                    break
                if i==cols[-1]:      #最近一年的线加粗
                    axes.plot(df.index[:self.currentday+1],df[i][:self.currentday+1],color='k',linewidth=3,label=i)
                else:
                    axes.plot(df.index,df[i],color=next(colors),linewidth=2,label=i)
                count+=1
            axes.xaxis.set_major_formatter(mdate.DateFormatter('%b'))
            #axes.legend(loc='best',fontsize=10,title=next(legendtitle))
            if ax==0:
                axes.set_title(next(legendtitle))
                axes.legend(loc='lower center', bbox_to_anchor=(0.5,-0.17),ncol=count) #bbox_to_anchor位置参数需要尝试,我也不知道哪个参数显示得好看
            else:
                axes.set_title(next(legendtitle))
            ax+=1
        plt.show()
        return 'plot finished !'

if __name__ == "__main__":
    cls=ssl('RB10','J09','1','1','2010',True,'rto')
    df=cls.plot()
    #df.to_csv('test01.csv')
    #data=pd.DataFrame(df).T
    #data.to_csv('test.csv')
    #print df 