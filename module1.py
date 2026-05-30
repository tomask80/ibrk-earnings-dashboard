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
        self.historical_data[reqId]=[]
        if reqId not in self.historical_data:
            self.historical_data[reqId].append({
                'date' : bar.date,
                'open' : bar.open,
                'high' : bar.high,
                'low' : bar.low,
                'close': bar.close,
                'volume' : bar.volume
                })    
     
    def historicalDataEnd(self,reqId,start,end):
        print(f"Historical data received for reqId: {reqId}")


class EarningsTradingDashboard:
    
    def __init__(self,root):
        #main window
        self.root = root
        self.root.title("Earnings Trading Dashboard - IV Crush Analysis")
        self.root.geometry('1600x1000')

        #Data storage
        self.stock_data = None
        self.vix_data = None
        self.iv_data = None
        self.earnings_data = None
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

        self.root.columnconfigure(0,weight =1)
        self.root.rowconfigure(0,weight=1)
        main_frame.columnconfigure(1,weight=1)
        main_frame.rowconfigure(8,weight = 1)

        # Connection
        conn_frame = ttk.LabelFrame(main_frame,text = "Interactive Brokers Connection",padding="5") #widget
        conn_frame.grid(row = 0,column= 0,columnspan=2,sticky=(tk.W,tk.E),pady=(0,10))

        ttk.Label(conn_frame,text = "Host: ").grid(row=0,column=0,padx=(0,5))
        self.host_var = tk.StringVar(value = '127.0.0.1')
        ttk.Entry(conn_frame,textvariable=self.host_var,width=15).grid(row=0,column=1,padx=(0,10))

        ttk.Label(conn_frame,text = "Port: ").grid(row=0,column=2,padx=(0,5))
        self.port_var = tk.StringVar(value = '7497')
        ttk.Entry(conn_frame,textvariable=self.port_var,width=15).grid(row=0,column=3,padx=(0,10))

        self.connect_btn = ttk.Button(conn_frame,text = "Connect",command = self.connect_ib)
        self.connect_btn.grid(row=0,column=4,padx=(0,10))

        self.disconnect_btn = ttk.Button(conn_frame,text='Disconnect',command=self.disconnect_ib,state = 'disabled')
        self.disconnect_btn.grid(row = 0,column=5)

        #Earnings Analysis Label Frame
        earnings_frame = ttk.LabelFrame(main_frame,text ="Earnings Analysis Setup",padding = "5")
        earnings_frame.grid(row =1,column = 0,columnspan=2,sticky=(tk.E,tk.W),pady=(0,10))
        
        ttk.Label(earnings_frame,text = "Ticker: ").grid(row=0,column=0,padx=(0,5))
        self.ticker_var = tk.StringVar(value = 'NVDA')
        ttk.Entry(earnings_frame,textvariable=self.ticker_var,width=10).grid(row=0,column=1,padx=(0,10))
        
        ttk.Label(earnings_frame,text = "Earnings Date: ").grid(row=0,column=2,padx=(0,5))
        self.earnings_date_var = tk.StringVar(value = '2025-08-27') #earnings date for NVDA
        ttk.Entry(earnings_frame,textvariable=self.earnings_date_var,width=12).grid(row=0,column=3,padx=(0,10))
        
        ttk.Label(earnings_frame,text = "Days to Expiry: ").grid(row=0,column=4,padx=(0,5))
        self.days_to_expiry_var = tk.StringVar(value = '30') 
        ttk.Entry(earnings_frame,textvariable=self.days_to_expiry_var,width=12).grid(row=0,column=5,padx=(0,10))
        
        self.analyze_btn= ttk.Button(earnings_frame,text="Analyze IV Crush",command=self.analyze_iv_crush,state = 'disabled')
        self.analyze_btn.grid(row=0,column=6)
        
        # Current Metrics Section
        metrics_frame = ttk.LabelFrame(main_frame,text= "Current Metrics",padding="5")
        metrics_frame.grid(row=2,column=0,columnspan=2,sticky=(tk.W,tk.E),pady=(0,10))
        
        ttk.Label(metrics_frame,text="Stock Price:").grid(row=0,column=0,padx=(0,5))
        self.stock_price_label = ttk.Label(metrics_frame,text ="N/A",font=("Arial",10,"bold"))
        self.stock_price_label.grid(row=0,column= 1,padx=(0,20))
        
        ttk.Label(metrics_frame,text="VIX level:").grid(row=0,column=2,padx=(0,5))
        self.vix_level_label = ttk.Label(metrics_frame,text ="N/A",font=("Arial",10,"bold"))
        self.vix_level_label.grid(row=0,column= 3,padx=(0,20))
        
        ttk.Label(metrics_frame,text="Current IV:").grid(row=0,column=4,padx=(0,5))
        self.current_iv_level = ttk.Label(metrics_frame,text ="N/A",font=("Arial",10,"bold"))
        self.current_iv_level.grid(row=0,column= 5,padx=(0,20))
        
        # IV Crush Analysis
        crush_frame = ttk.LabelFrame(main_frame,text="IV Crush Analysis",padding="5")
        crush_frame.grid(row=3,column =3, columnspan = 2,sticky=(tk.E,tk.E),pady = (0,10))
        
        ttk.Label(crush_frame,text="Pre-Earnings IV:").grid(row=0,column=0,padx=(0,5))
        self.pre_iv_label = ttk.Label(crush_frame,text ="N/A",font=("Arial",10,"bold"))
        self.pre_iv_label.grid(row=0,column= 1,padx=(0,20))
        
        ttk.Label(crush_frame,text="Post-Earnings IV:").grid(row=0,column=2,padx=(0,5))
        self.post_iv_label = ttk.Label(crush_frame,text ="N/A",font=("Arial",10,"bold"))
        self.post_iv_label.grid(row=0,column= 3,padx=(0,20))
        
        ttk.Label(crush_frame,text="IV Crush %:").grid(row=0,column=4,padx=(0,5))
        self.iv_crush_level = ttk.Label(crush_frame,text ="N/A",font=("Arial",10,"bold"),foreground='red')
        self.iv_crush_level.grid(row=0,column= 5,padx=(0,20))
        
        #Spot vs Strike
        spot_strike_frame= ttk.LabelFrame(main_frame,text="Spot vs Strike Analysis",padding = "5")
        spot_strike_frame.grid(row=4,column=0,columnspan=2,sticky=(tk.W,tk.E),pady=(0,10))
        
        ttk.Label(spot_strike_frame,text="Strike Price:").grid(row=0,column=0,padx=(0,5))
        self.strike_price_label = ttk.Label(spot_strike_frame,text ="N/A",font=("Arial",10,"bold"))
        self.strike_price_label.grid(row=0,column= 1,padx=(0,20))
        
        ttk.Label(spot_strike_frame,text="Post-Earnings Spot (Close):").grid(row=0,column=2,padx=(0,5))
        self.pre_spot_label = ttk.Label(spot_strike_frame,text ="N/A",font=("Arial",10,"bold"))
        self.pre_spot_label.grid(row=0,column= 3,padx=(0,20))
        
        ttk.Label(spot_strike_frame,text="Post-Earnings Spot (Next Day Avg):").grid(row=0,column=4,padx=(0,5))
        self.post_spot_label = ttk.Label(spot_strike_frame,text ="N/A",font=("Arial",10,"bold"))
        self.post_spot_label.grid(row=0,column= 5,padx=(0,20))
        
        # Options Pricing Frame
        option_frame = ttk.LabelFrame(main_frame,text="ATM Straddle Pricing & P/L",padding="5")
        option_frame.grid(row=5,column=0,columnspan=2,sticky=(tk.W,tk.E),pady=(0,10))
        
        ttk.Label(option_frame,text="Pre-Earnings Call:").grid(row=0,column=0,padx=(0,5))
        self.pre_call_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.pre_call_label.grid(row=0,column= 1,padx=(0,20))
        
        ttk.Label(option_frame,text="Post-Earnings Call:").grid(row=0,column=2,padx=(0,5))
        self.post_call_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.post_call_label.grid(row=0,column= 3,padx=(0,20))
        
        ttk.Label(option_frame,text="Call Change:").grid(row=0,column=4,padx=(0,5))
        self.call_loss_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.call_loss_label.grid(row=0,column= 5,padx=(0,20))
        #puts
        ttk.Label(option_frame,text="Pre-Earnings Put:").grid(row=1,column=0,padx=(0,5))
        self.pre_put_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.pre_put_label.grid(row=1,column= 1,padx=(0,20))
        
        ttk.Label(option_frame,text="Post-Earnings Put:").grid(row=1,column=2,padx=(0,5))
        self.post_put_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.post_put_label.grid(row=1,column= 3,padx=(0,20))
        
        ttk.Label(option_frame,text="Put Change:").grid(row=1,column=4,padx=(0,5))
        self.put_loss_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.put_loss_label.grid(row=1,column= 5,padx=(0,20))
        
        # Straddle
        ttk.Label(option_frame,text="Pre-Earnings Straddle:").grid(row=2,column=0,padx=(0,5))
        self.pre_straddle_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.pre_straddle_label.grid(row=2,column= 1,padx=(0,20))
        
        ttk.Label(option_frame,text="Post-Earnings Straddle:").grid(row=2,column=2,padx=(0,5))
        self.post_straddle_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.post_straddle_label.grid(row=2,column= 3,padx=(0,20))
        
        ttk.Label(option_frame,text="Straddle Change:").grid(row=2,column=4,padx=(0,5))
        self.straddle_loss_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.straddle_loss_label.grid(row=2,column= 5,padx=(0,20))
        
        #straddle P/L
        ttk.Label(option_frame,text="LONG Straddle P/L:").grid(row=3,column=0,padx=(0,5))
        self.long_pnl_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.long_pnl_label.grid(row=3,column= 1,columnspan=2,padx=(0,20))
        
        ttk.Label(option_frame,text="SHORT Straddle P/L:").grid(row=3,column=3,padx=(0,5))
        self.short_pnl_label = ttk.Label(option_frame,text ="N/A",font=("Arial",10,"bold"))
        self.short_pnl_label.grid(row=3,column= 4,columnspan=2,padx=(0,20))
        
        #Greeks Frame
        greeks_frame= ttk.LabelFrame(main_frame,text="Greeks Analysis",padding = "5")
        greeks_frame.grid(rows = 6,column=0,columnspan=2,sticky=(tk.W,tk.E),pady=(0,10))
        
        ttk.Label(greeks_frame,text="Pre-Earnings Detla:").grid(row=0,column=0,padx=(0,5))
        self.pre_delta_label = ttk.Label(greeks_frame,text ="N/A",font=("Arial",10,"bold"))
        self.pre_delta_label.grid(row=0,column= 1,padx=(0,20))
        
        ttk.Label(greeks_frame,text="Post-Earnings Delta:").grid(row=0,column=2,padx=(0,5))
        self.post_delta_label = ttk.Label(greeks_frame,text ="N/A",font=("Arial",10,"bold"))
        self.post_delta_label.grid(row=0,column= 3,padx=(0,20))
        
        ttk.Label(greeks_frame,text="Delta Change:").grid(row=0,column=4,padx=(0,5))
        self.delta_change_label = ttk.Label(greeks_frame,text ="N/A",font=("Arial",10,"bold"))
        self.delta_change_label.grid(row=0,column= 5,padx=(0,20))
        
        # Vega
        ttk.Label(greeks_frame,text="Pre-Earnings Vega:").grid(row=1,column=0,padx=(0,5))
        self.pre_vega_label = ttk.Label(greeks_frame,text ="N/A",font=("Arial",10,"bold"))
        self.pre_vega_label.grid(row=1,column= 1,padx=(0,20))
        
        ttk.Label(greeks_frame,text="Post-Earnings Vega:").grid(row=1,column=2,padx=(0,5))
        self.post_vega_label = ttk.Label(greeks_frame,text ="N/A",font=("Arial",10,"bold"))
        self.post_vega_label.grid(row=1,column= 3,padx=(0,20))
        
        ttk.Label(greeks_frame,text="Vega Change:").grid(row=1,column=4,padx=(0,5))
        self.vega_change_label = ttk.Label(greeks_frame,text ="N/A",font=("Arial",10,"bold"))
        self.vega_change_label.grid(row=1,column= 5,padx=(0,20))
        
        # Status
        status_frame = ttk.LabelFrame(main_frame,text="Status",padding ="5")
        status_frame.grid(rows = 7,column=0,columnspan=2,sticky=(tk.W,tk.E),pady=(0,10))
        
        self.status_text = scrolledtext.ScrolledText(status_frame,height = 6, width = 80)
        self.status_text.grid(row=0,column=0,sticky=(tk.W,tk.E))
        status_frame.columnconfigure(0,weight=1)
        
        plot_frame = ttk.LabelFrame(main_frame,text="IV Crush Visualization",padding="5")
        plot_frame.grid(row=8,column= 0,columnspan=2,sticky =(tk.E,tk.N,tk.W,tk.S))
        plot_frame.columnconfigure(0,weight=1)
        plot_frame.rowconfigure(0,weight=1)
        
        self.fig, (self.ax1,self.ax2) = plt.subplots(1,2,figsize=(16,6))
        self.canvas = FigureCanvasTkAgg(self.fig,plot_frame)
        self.canvas.get_tk_widget().grid(row=0,column=0,sticky=(tk.E,tk.N,tk.W,tk.S))
        
        # 1.22.44
    def log_message(self,message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END,f"[{timestamp}]{message}\n")
        self.status_test.see(tk.END)
        self.root.update_idletasks()
        
    def connect_ib(self):
        try:
            host = self.host_var.get()
            port = int(self.port_var.get())
            self.log_message(f"Connecting to IB at {host}:{port}")
            
            def connect_thread():
                try:
                    self.ib_app.connect(host,port,0)
                    self.ib_app.run()
                except Exception as e:
                    self.log_message(f"Connection erro: {e}")
            
            thread = threading.Thread(target=connect_thread,daemon=True)
            thread.start()
            
            for i in range(100):
                if self.ib_app.connected:
                    try:
                        server_version = self.ib_app_serverVersion()
                        if server_version is not None and server_version > 0:
                            break
                    except:
                        pass
                time.sleep(.1)
                
            if self.ib_app.connected:
                try:
                    server_version = self.ib_app.serverVersion()
                    if server_version is not None and server_version > 0:
                        self.connected = True
                        self.connect_btn.config(state = 'disabled')
                        self.disconnect_btn.config(state = 'normal')
                        self.analyze_btn.config(state='normal')
                        self.log_message(f"Successfully connected to IB Server Version: {server_version}")
                    else:
                        self.log_message("Connected, but server version unavaible")
                except Exception as e:
                    self.log_message(f"Connected to the server, but server version check failed: {e}")
            else:
                self.log_message("Failed to connect tp Interactive Brokers")
                
        except Exception as e:
            self.log_message(f"Connection Erro: {e}")       
                    
                    
    def disconnect_ib(self):
        try:
            self.ib_app.disconnect()
            self.connect = False
            self.connect_btn.config(state='normal')
            self.disconnect_btn.config(state ='disabled')
            self.analyze_btn.config(state='disable')
            
            self.clear_analysis_results()
            
            self.log_message('Disconnected from Interactive Brokers')
        except Exception as e:
            self.log_message(f"Disconnect Error: {e}")
            
    # 1:34.53