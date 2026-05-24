import tkinter as tk
from tkinter import ttk,messagebox,scrolledtext
import threading
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from datetime import datetime,timedelta
import warnings
warnings.filterwarnings('ignore')

class IBApp(EWrapper,EClient):
    
    def __init__(self):
        EClient.__init__(self,self)
        self.connected =False
        self.historical_data ={}

    def error(self,reqId,errorCode,errorString, *args):
        if errorCode == 2176 and "fractional share" in errorString.lower():
            return
        print(f"Reqid: {reqId}| Error: {errorCode}: {errorCode} | Msg: {errorString}")
        if args:
            print(f"Additional error information {args}")

    def nextValidId(self,orderID):
        self.connected = True
        print("Connect to IB")

    def historicalData(self,reqId,bar):
        if reqId not in self.historical_data:
            self.historical_data[reqId].append({
                'date' : bar.date,
                'open' : bar.open,
                'high' : bar.hight,
                'low' : bar.low,
                'close': bar.close,
                'volume' : bar.volume
                })    
     
    def historicalDataEnd(self,reqId,start,end):
        print(f"Historical data received for reqId: {reqId}")


class EarningsTradingDashboard:
    
    def __int__(self,root):
        #main window
        self.root = root
        self.root.title("Earnings Trading Dashboard - IV Crush Analysis")
        self.root.geometry('1600x1000')

        #Data storage
        self.stock_data = None
        self.vix_data = None
        self.iv_data = None
        self.earnigns_data = None
        self.ticker = None
        
        self.ib_app = IBApp()
        self.connected = False

        self.risk_free_rate = .05

        self.ax1_twin = None

        self.setup_ui()

    def create_equity_contract(self,symbol):
        contract = Contract()
        contract.symbol =symbol.upper()
        contract.secType ='STK'
        contract.exchange = 'SMART'
        contract.currency = 'USD'
        return contract

    def create_vix_contract(self):
        contract = Contract()
        contract.symbol = 'VIX'
        contract.secType = 'IND'
        contract.exchange = 'CBOE'
        contract.currency = 'USD'
        return contract

    def setup_ui(self):
        main_frame =ttk.Frame(self.root,padding= "10")
        main_frame.grid(row=0,column=0,sticky=(tk.W,tk.E,tk.N,tk.S))

        self.root.columnonfigure(0,weight =1)
        self.root.rowconfigure(0,weight=1)
        main_frame.columnconfigure(1,weight=1)
        main_frame.rowconfigure(8,weight = 1)

        # Connection
        conn_frame = ttk.LabelFrame(main_frame,text = "Interactive Brokers Connection",padding="5") #widget
        conn_frame.grid(row = 0,column= 0,columnspan=2,sticky=(tk.W,tk.E),pady=(0,10))

        ttk.Label(conn_frame,text = "Host: ").grid(row=0,column=0,padx=(0,5))
        self.host_var = tk.StringVar(value = '127.0.0.1')
        ttk.Entry(conn_frame,textvariable=self.host_var,widget=15).grid(row=0,column=1,padx=(0,10))

        ttk.Label(conn_frame,text = "Port: ").grid(row=0,column=2,padx=(0,5))
        self.host_var = tk.StringVar(value = '7497')
        ttk.Entry(conn_frame,textvariable=self.host_var,widget=15).grid(row=0,column=3,padx=(0,10))

        self.connect_btn = ttk.Button(conn_frame,text = "Connect",command = self.connect_ib)
        self.connect_btn.grid(row=0,column=4,padx(0,10))

        self.disconnect_btn = ttk.Button(conn_frame,text='Disconnect',commant=self.disconnect_ib,state = 'disabled')
        self.disconnect_btn.grid(row = 0,column=5)

        #Earnings Analysis Label Frame
        earnigns_frame = ttk.LabelFrame(main_frame,text ="Earnings Analysis Setup",padding = "5")
        earnings_frame.grid(row =1,column = 0,columnspan=2,sticky=(tk.E,tk.W),pady=(0,10))