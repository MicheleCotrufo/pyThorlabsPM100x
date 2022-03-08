### v0.1 (2022-02-15)


import PyQt5.QtWidgets as Qt# QApplication, QWidget, QMainWindow, QPushButton, QHBoxLayout
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import pyqtgraph as pg
import logging


class PlotObject:
    def __init__(self,  app,  mainwindow, parent):#, GetData, GetNameData, GetPlotConfig, SetPlotConfig, GetPlottingStyle, PlotSize, **kwargs):
        # app           = The pyqt5 QApplication() object
        # mainwindow    = Main Window of the application
        # parent        = a QWidget (or QMainWindow) object that will be the parent for the gui of this device.

        #GetData, GetNameData, GetPlotsConfig, SetPlotsConfig are functions, which normally are defined as methods of the MainWindow object, and they let this PlotObject read the data and read/set the PlotsConfig
        #super().__init__(master,**kwargs)
        #self.PlotContainer = master # = the PlotContainer object/frame which contains this PlotObject
        self.mainwindow = mainwindow
        self.app = app
        self.parent = parent
        
        self.ConfigPopupOpen = 0 #This variable is 1 when the popup for plot configuration is open, and 0 otherwise

        #self.GetData = GetData
        #self.GetNameData = GetNameData
        #self.GetPlotConfig = GetPlotConfig
        #self.SetPlotConfig = SetPlotConfig
        #self.GetPlottingStyle = GetPlottingStyle

        self.Max = 0 #Keep track of the maximum of minimum values plotted in this plot (among all possible curves). It is used for resizing purposes
        self.Min = 0

        #self.PlotErrorBars_var = tk.IntVar(value=1) #This TK variable keeps track of wheter the user wants to plot the errorbars or not

        #Create the figure

        self.graphWidget = pg.PlotWidget()
        self.graphWidget.showGrid(x=True, y=True)
        #self.graphWidget.setMenuEnabled(False)
        vbox = Qt.QVBoxLayout()
        vbox.addWidget(self.graphWidget) 
        #vbox.addStretch(1)

        self.parent.setLayout(vbox)

        X = []
        Y = []


        ## plot data: x, y values
        self.data = self.graphWidget.plot(X,Y)

        #self.fig = Figure(figsize=[ 8, 6 ] dpi=100)
        #self.fig.set_tight_layout(True)
        #self.ax = self.fig.add_subplot(111,facecolor='black')
        #self.canvas = FigureCanvasTkAgg(self.fig, master=self)  # A tk.DrawingArea.
        
        
        #self.grid_columnconfigure(0, weight=1)
        #self.grid_rowconfigure(0, weight=1)
        #graph_widget = self.canvas.get_tk_widget()
        #graph_widget.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        ##self.config(highlightbackground = "red", highlightcolor= "red", highlightthickness=1,bd=1)
        

        #PlotConfig = self.GetPlotConfig()          #PlotConfig specifies what is plotted in the plot, as defined in each element of the list PlotsConfig in config.py
        #                                            #This configuration is stored as a property of the MainWindow, and can also be changed by the user after the application is started

        #self.FramePlotControls = tk.Frame(self)
        #self.FramePlotControls.grid(row=1, column=0,pady=1,padx=0,sticky=tk.W)
        
        #if not(type(PlotConfig )==int):         #If PlotConfig is an integer, then this plot has been assigned directly to an instrument, and we don't want to manipulate it further 
        #                                        #If PlotConfig is not an integer, then this plot is meant to show acquired data, and we add a 'Configure Plot' button to let the user choose the data to plot
        #    self.UpdateInternalVariables()
        #    self.iconConfigure = tk.PhotoImage(file = r"graphics\settings_icon.png") 
        #    self.ButtonConfigure = tk.Button(self.FramePlotControls, text="", image = self.iconConfigure, command=lambda:self.popup_Config(self.ButtonConfigure))
        #    self.ButtonConfigure.pack(fill=tk.X, side=tk.LEFT,padx=2,pady=0)
        #    self.canvas.draw()

        #    self.iconResizeY_MinMax = tk.PhotoImage(file = r"graphics\resize_min_max_icon.png") 
        #    self.ButtonResizeY_MinMax = tk.Button(self.FramePlotControls, image = self.iconResizeY_MinMax, command=self.ResizeY)
        #    self.ButtonResizeY_MinMax.pack(fill=tk.X, side=tk.LEFT,padx=2,pady=0)

        #    self.iconResizeY_ZeroMax = tk.PhotoImage(file = r"graphics\resize_0_max_icon.png") 
        #    self.ButtonResizeY_ZeroMax = tk.Button(self.FramePlotControls,  image = self.iconResizeY_ZeroMax, command=lambda:self.ResizeY(Min=0))
        #    self.ButtonResizeY_ZeroMax.pack(fill=tk.X, side=tk.LEFT,padx=2,pady=0)
        #self.canvasNavigationToolbar = NavigationToolbar2Tk(self.canvas, self.FramePlotControls,pack_toolbar=False)
        #self.canvasNavigationToolbar.children['!button3'].pack_forget()
        #self.canvasNavigationToolbar.children['!button2'].pack_forget()
        #self.canvasNavigationToolbar.children['!button4'].pack_forget()
        #self.canvasNavigationToolbar.pack(fill=tk.X, side=tk.LEFT,padx=2,pady=0)

    #def UpdateInternalVariables(self):
    #    '''
    #    Based on the current values of the PlotConfig of this plot, we update the lists self.ListIntVars_YAxis and self.ListIntVars_XAxis, which are used for the popup config menu
    #    '''
    #    #Each data in NameData is a potential y-data or x-data for the plot. We create a list of tk.IntVar variables to keep track if each data in NameData is currently being plotted here
    #    NameData = self.GetNameData() 
    #    PlotConfig = self.GetPlotConfig()
    #    self.ListIntVars_YAxis =[]
    #    for data in NameData:
    #        if (data in PlotConfig[1:]): #self.PlotConfig[1:] contains the names of all data currently plot on Y axis for this plot
    #            self.ListIntVars_YAxis.append(tk.IntVar(value=1))
    #        else:
    #            self.ListIntVars_YAxis.append(tk.IntVar(value=0))

    #    self.IntVar_XAxis = tk.IntVar(value=0)
    #    for index,data in enumerate(NameData):
    #        if (data == PlotConfig[0]): #self.PlotConfig[0] contains the names of the data which is currently used for the X axis for this plot
    #            self.IntVar_XAxis.set(index) #the value of IntVar_XAxis is set to the index of the data currently used for x axis

    #def UpdatePlotConfig(self):
    #    '''
    #    This function does the opposite of UpdateInternalVariables. Based on the current values of the lists self.ListIntVars_YAxis and self.ListIntVars_XAxis ( which are used for the popup config menu)
    #    it updates the value of PlotConfig
    #    '''
    #    PlotConfig =[]
    #    NameData = self.GetNameData() 
    #    #The first element in PlotConfig is the name of the variable used for x axis
    #    Data_X_Axis = NameData[self.IntVar_XAxis.get()]
    #    PlotConfig.append(Data_X_Axis)

    #    #Now se scan over self.ListIntVars_YAxis, and everytime a variable is set to 1 we add the corresponding dataname to self.PlotConfig
    #    for i,var in enumerate(self.ListIntVars_YAxis):
    #        if var.get()==1:
    #            PlotConfig.append(NameData[i])

    #    self.SetPlotConfig(PlotConfig)


    #def UpdatePlot(self):
    #    '''
    #    We refresh the plot content
    #    In this function we look at all the datanames in PlotConfig, we identify the corresponding index of the same dataname in NameData, and we use this index to extract the data column fron Data 
    #    and the style from DataPlottingStyle
    #    '''
    #    PlotConfig = self.GetPlotConfig()
    #    Data = self.GetData()[0]
    #    Data_STD = self.GetData()[1]
    #    DataPlottingStyle = self.GetPlottingStyle()
    #    NameData = self.GetNameData() 

    #    self.ax.clear()

                                            
    #    #NameData contains the name of all acquired data, in the same format used in the list PlotConfig. 
    #    #We use NameData to find the corresponding index of the x data and of the y-, in order to extract the correct columns from Data 
    #    #This index also identifies the corresponding plot style in the list DataPlottingStyle

    #    #The first element of the list PlotConfig always represents the variable to use for x axis
    #    XData_index =  NameData.index(PlotConfig[0])
    #    x = Data[:,XData_index]
    #    xerr = Data_STD[:,XData_index]
    #    numcolLeg = 0
    #    for i in range(1,len(PlotConfig)):
    #        YData_index = NameData.index(PlotConfig[i])
    #        y =  Data[:,YData_index]
    #        if(len(y) > 0 and i==1):
    #            self.Max = max(y) 
    #            self.Min = min(y)
    #        if len(y) > 0 and i>1:
    #            if max(y) > self.Max:
    #                self.Max = max(y)
    #            if min(y) < self.Min:
    #                self.Min = min(y)
    #        yerr = Data_STD[:,YData_index]
    #        self.Plot(x=x, y=y, xerr=xerr, yerr=yerr, label=PlotConfig[i], **(DataPlottingStyle[YData_index]))
    #        numcolLeg = numcolLeg + 1

    #    if(numcolLeg>0):
    #        numcolLeg = min(4,numcolLeg) #Here we make sure that there are maximum 4 columns (otherwhise the plot window gets distorted)
    #        leg = self.ax.legend( bbox_to_anchor=(-0.1, -0.22, 0.2, .102), loc='lower left',
    #                    borderaxespad=0.,facecolor='black', ncol=numcolLeg, fontsize = 8)
    #        for text in leg.get_texts():
    #            plt.setp(text, color = 'w')
    #    self.ax.grid(color='white',linestyle= '--', linewidth =0.5)
  
    #    self.ax.set_xlabel(PlotConfig[0], fontsize=12)

    #    self.canvas.draw()

    #def ResizeY(self,Min=None,Max=None):
    #    if Min == None:
    #        Min = self.Min
    #    if Max == None:
    #        Max = self.Max
    #    self.ax.set_ylim((0.9*Min, 1.1*Max))
    #    self.canvas.draw()


    #def Plot(self,x,y,xerr,yerr,label,**kwargs):
    #    '''
    #    This function plots a single line in the axes specified by ax. It uses either ax.plot() or ax.errorbar() depending on the value of self.PlotErrorBars_var.get()
    #    '''
    #    if self.PlotErrorBars_var.get()==1: #If the user wants to plot errorbars
    #        self.ax.errorbar(x,y,xerr=xerr,yerr=yerr,label=label,**kwargs)
    #    else:
    #        self.ax.plot(x,y,label=label,**kwargs)

    #def popup_Config(self,bt):
    #    ''' It opens a popup menu to specify what to plot on x and y axis in this plot. The popup menu automatically updates the property self.PlotConfig
    #    '''
    #    NameData = self.GetNameData() 
    #    if self.ConfigPopupOpen == 0: #when this variable is zero, the popup is closed, and we want to open it
    #        self.ConfigPopupOpen = 1
            
    #        self.popup = tk.Toplevel()
    #        self.popup.wm_title("Configure Plot")
    #        self.popup.focus_set() #Make sure the popup has already the focus, so it will loses focus if we click anywhere else
    #        self.popup.overrideredirect(True) #This removes the top bar of the window
            
    #        self.popup.labelXaxis = tk.Label(self.popup, text="X axis")
    #        self.popup.labelXaxis.grid(row=0,column=0, sticky=tk.N+tk.S+tk.E+tk.W,pady=1,padx=5) 

    #        self.popup.labelYaxis = tk.Label(self.popup, text="Y axis")
    #        self.popup.labelYaxis.grid(row=0,column=1, sticky=tk.N+tk.S+tk.E+tk.W,pady=1,padx=5) 

    #        self.popup.labelAdditionalSettings = tk.Label(self.popup, text="Settings")
    #        self.popup.labelAdditionalSettings.grid(row=0,column=2, sticky=tk.N+tk.S+tk.E+tk.W,pady=1,padx=5) 

    #        for i,name in enumerate(NameData):
    #            rdbt = tk.Radiobutton(self.popup, text=name, variable=self.IntVar_XAxis, value=i, command=lambda:[self.UpdatePlotConfig(),self.UpdatePlot()])
    #            rdbt.grid(row=i+1,column=0, sticky=tk.W,pady=1,padx=5)


    #            ckbt = tk.Checkbutton(self.popup, variable=self.ListIntVars_YAxis[i], text=name, command=lambda:[self.UpdatePlotConfig(),self.UpdatePlot()])
    #            ckbt.grid(row=i+1,column=1, sticky=tk.W,pady=1,padx=5)

    #        ckbtErrorBar = tk.Checkbutton(self.popup, variable=self.PlotErrorBars_var, text="Plot error bars", command=self.UpdatePlot)
    #        ckbtErrorBar.grid(row=1,column=2, sticky=tk.W,pady=1,padx=5)

    #        self.popup.withdraw()
    #        self.popup.update()
    #        x = bt.winfo_rootx()
    #        y = bt.winfo_rooty()
    #        bt_h = bt.winfo_height()
    #        win_h = self.popup.winfo_height()
    #        win_w = self.popup.winfo_width()
    #        y = y - win_h
    #        #x = x - win_w
    #        self.popup.geometry(f'+{x}+{y}')

    #        # Binding to close the menu if user does something else
    #        self.popup.bind("<FocusOut>", self.close_popup)  # User focus on another window
    #        self.popup.bind("<Escape>", self.close_popup)    # User press Escape
    #        self.popup.protocol("WM_DELETE_WINDOW", self.close_popup)


    #        self.popup.deiconify()
            
    #    else:
    #        self.ConfigPopupOpen = 0
    #        self.popup.destroy()


    #def close_popup(self, event=None):
    #    self.ConfigPopupOpen = 0
    #    self.popup.destroy()
    #    self.MainWindow.master.focus_set()
        
            


#class PlotContainer(tk.Frame): #Container for Plots, which is also a TK frame

#    def __init__(self, master, MainWindow, NumberPlots, PlotsSizes, NCols,**kwargs):
#        super().__init__(master,**kwargs)
#        self.master = master #= Containing Frame
#        self.MainWindow = MainWindow #= MainWindow

#        #Create all plots. To each plot we assign functions that will allow the plot to retrieve data, and to read and set its own PlotConfig. The PlotConfig of all plots are always stored in the MainWindow object

#        self.ListPlots = [] #This will contain the PlotObject object (see class defined above) of each plot contained in this container 
#        for i in np.arange(0,NumberPlots):
#            NewPlot = PlotObject(self, MainWindow, GetData = MainWindow.GetCurrentData, GetNameData = MainWindow.GetNameData, 
#                                 GetPlotConfig=lambda i=i:MainWindow.GetPlotConfig(i), SetPlotConfig=lambda x,i=i:MainWindow.SetPlotConfig(i,x), 
#                                 GetPlottingStyle = MainWindow.GetDataPlottingStyle, PlotSize=PlotsSizes[i])
#            NewPlot.config(highlightbackground = "black", highlightcolor= "black", highlightthickness=1,bd=1)
#            NewPlot.grid(row=i//NCols,column=i%NCols, sticky=tk.N+tk.S+tk.E+tk.W)
#            self.ListPlots.append(NewPlot)
#        for i in range(0,NCols):
#            self.grid_columnconfigure(i, weight=1)
#        self.grid_rowconfigure(0, weight=1)

#    def UpdateAllPlots(self,WhichPlot=None):

#        if(not(WhichPlot==None)):
#            Plot.UpdatePlot()
#        else:
#            for PlotIndex, Plot in enumerate(self.ListPlots): #Iterate over all the plots objects 
#                PlotConfig = self.MainWindow.GetPlotConfig(PlotIndex) #PlotConfig describes what will be plotted in this plot, with the same format as each element of the list PlotsConfig in config.py
#                if not(type(PlotConfig)==int): #If PlotConfig is an integer, it identifies an instrument. It means that this plot is assigned to an instrument and we will not touch it.
#                                                # If PlotConfig is not an integer, then it is a list. It means that the plot is not assigned to an instrument, but is instead used to show acquired data,
#                                                # and the acquired data to show in this plot is contained in the list Plot.PlotConfig (see config.py file)
#                                                #For example, PlotConfig  =  [ 'Dev1_Power', 'Dev0_Pk2PkCH1', 'Dev0_Pk2PkCH1']
#                    Plot.UpdatePlot()

#    def Draw(self):
#        '''
#        Call the draw() function of all canvas
#        '''
#        for i,Plot in enumerate(self.ListPlots):
#            Plot.canvas.draw()