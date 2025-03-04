"""
    #PEA

    PEA is a Python Emulator for Audiovisual devices written to aid
    in the develpment and testing of Audiovisual control projects.

    Code by: 
        Alex Teusch - alexander.teusch@gmail.com
        Rupert Powell - rupert@astronoscope.eu

    VerticalScrollFrame by:
        http://tkinter.unpythonic.net/wiki/VerticalScrolledFrame

    Version controlled here:
        https://github.com/clydefrog76/pea

    PEA  Copyright (C) 2020 by Alex Teusch & Rupert Powell
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os, sys, json, time, ast, datetime, binascii, asyncio, platform, shlex, importlib
import tkinter.ttk as ttk
from tkinter import Tk, filedialog, messagebox, VERTICAL, TRUE, FALSE, Text, Canvas, Frame, Menu, PhotoImage, NW, YES, BOTH, LEFT, RIGHT, END, TOP, BOTTOM, Y, X, Toplevel, IntVar, TclError, StringVar


async def run_tk(root, interval=0.01):
    """
    Run a tkinter app in an asyncio event loop.
    """
    try:
        while root.winfo_exists():  # Window not closed
            root.update()
            await asyncio.sleep(interval)
    except TclError as e:
        if "application has been destroyed" not in e.args[0]:
            raise


class Window(Frame):
    def __init__(self, master=None):
        """ create the master frame class """

        Frame.__init__(self, master)
        self.master = master
        self.init_window()

    def init_window(self):
        """ declare the main window for gui drawing """

        self.master.title("PEA - Python Emulator for Audiovisual devices")
        #self.master.iconbitmap(r'assets/icon.png') 
        self.pack(fill=BOTH, expand=1)
        self.colorList = ["#FF0000", "#00FF00", "#DDEEFF", "#009900", "#000099"]
        self.terminalrunning = True
        self.commandsList = None
        self.devscript = None
        
        self.port = {"listen": 0, "connected": 0}
        self.portopen = False
        self.mySocket = None
        self.loop = None   
        self.logmodeactive = IntVar()
        self.showbytecount = IntVar()
        self.fname = None

        # menu bar section ----------------------------------------------------

        menubar = Menu(root)
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Browse for Emulator JSON File", command=self.browseFunction)
        filemenu.add_separator()
        filemenu.add_command(label="Exit PEA", command=on_closing)
        menubar.add_cascade(label="File", menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(label="Emulator JSON Editor", command=self.jsoneditorWindow)
        editmenu.add_command(label="Reload JSON", command=self.reloadJSON)
        editmenu.add_separator()
        editmenu.add_command(label="Emulator Script Editor", command=self.launchScriptEditor)
        editmenu.add_command(label="Reload Script", command=self.reloadScript)
        menubar.add_cascade(label="Edit", menu=editmenu)        

        toolsmenu = Menu(menubar, tearoff=0)
        toolsmenu.add_command(label="ASCII - HEX Converter", command=self.asciihexWindow)
        toolsmenu.add_separator()
        toolsmenu.add_command(label="Standard ASCII Chart", command=lambda i=1: self.asciichartWindow(i))
        toolsmenu.add_command(label="Extended ASCII Chart", command=lambda i=2: self.asciichartWindow(i))
        menubar.add_cascade(label="Tools", menu=toolsmenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="How to use PEA", command=self.howtoWindow)
        helpmenu.add_separator()
        helpmenu.add_command(label="About PEA", command=self.aboutWindow)
        menubar.add_cascade(label="Help", menu=helpmenu)

        menubar.add_command(label="Donate", command=self.donationsWindow)        

        root.config(menu=menubar)  

        # top grid section --------------------------------------------------

        mainframe1 = ttk.Frame(self)
        mainframe1.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')

        fileframe = ttk.LabelFrame(mainframe1, text="Emulator JSON File",)
        fileframe.grid(row=0, column=0, padx=8, pady=8, sticky='nsew')
        self.filelabel = ttk.Label(fileframe, width=90)
        self.filelabel.config(text="No JSON file loaded", background=self.colorList[2], 
           borderwidth=1, relief="solid", anchor="center")
        self.filelabel.pack(padx=5, pady=5, side=LEFT)

        portframe = ttk.LabelFrame(mainframe1, text="TCP Port",)
        portframe.grid(row=0, column=1, padx=8, pady=8, sticky='nsew')
        portlabel = ttk.Label(portframe, text="Port")
        portlabel.pack(padx=5, pady=5, side=LEFT)
        self.portentry = ttk.Entry(portframe, width=6)
        self.portentry.insert(0, "0")
        self.portentry.pack(padx=5, pady=5, side=LEFT)        
        self.portbutton = ttk.Button(portframe,
            text="Open Port", width=13,
            command=lambda: asyncio.ensure_future(self.listenFunction()))
        self.portbutton.pack(padx=5, pady=5, side=LEFT)

        connectionframe = ttk.LabelFrame(mainframe1, text="TCP Connection",)
        connectionframe.grid(row=0, column=2, padx=8, pady=8, sticky='nsew')
        self.colorlabel = ttk.Label(connectionframe, width=3, text="")
        self.colorlabel.pack(padx=5, pady=5, side=LEFT)
        self.colorlabel.config(background=self.colorList[0])  
        self.disconnectbutton = ttk.Button(connectionframe,
            text="Disconnect", width=13,
            command=lambda: self.disconnectFunction()
        )
        self.disconnectbutton.pack(padx=5, pady=5, side=LEFT)
        self.disconnectbutton.config(state="disabled")

        # send grid section --------------------------------------------------

        mainframe2 = ttk.Frame(self)
        mainframe2.grid(row=1, column=0, padx=0, pady=0, sticky='nsew')

        sendframe = ttk.LabelFrame(mainframe2, text="Send Quick Command",)
        sendframe.grid(row=0, column=0, padx=8, pady=8, sticky='nsew')
        sendlabel = ttk.Label(sendframe, text="String")
        sendlabel.pack(padx=5, pady=5, side=LEFT)
        self.sendentry = ttk.Entry(sendframe, width=50)
        self.sendentry.insert(0, "Replace this with ASCII or HEX bytes with prefix \\x")
        self.sendentry.bind("<Button-1>", self.sendentry_click)
        self.sendentry.bind("<FocusIn>", self.sendentry_click)
        self.sendentry.pack(padx=5, pady=5, side=LEFT)        
        self.sendbutton = ttk.Button(sendframe,
            text="Send", width=13,
            command=lambda: self.sendFunction(),
        )
        self.sendbutton.pack(padx=5, pady=5, side=LEFT)

        scriptframe = ttk.LabelFrame(mainframe2, text="Script Function Buttons",)
        scriptframe.grid(row=0, column=1, padx=8, pady=8, sticky='nsew')

        self.func1Text = StringVar()
        self.func1Text.set("Func 1")
        self.scriptbutton1 = ttk.Button(scriptframe,
            textvariable=self.func1Text, width=11,
            command=lambda i=1: self.callCustomFunc(i),
        )
        self.scriptbutton1.pack(padx=5, pady=5, side=LEFT)

        self.func2Text = StringVar()
        self.func2Text.set("Func 2")
        self.scriptbutton2 = ttk.Button(scriptframe,
            textvariable=self.func2Text, width=11,
            command=lambda i=2: self.callCustomFunc(i),
        )
        self.scriptbutton2.pack(padx=5, pady=5, side=LEFT)

        self.func3Text = StringVar()
        self.func3Text.set("Func 3")
        self.scriptbutton3 = ttk.Button(scriptframe,
            textvariable=self.func3Text, width=11,
            command=lambda i=3: self.callCustomFunc(i),
        )
        self.scriptbutton3.pack(padx=5, pady=5, side=LEFT)

        self.func4Text = StringVar()
        self.func4Text.set("Func 4")
        self.scriptbutton4 = ttk.Button(scriptframe,
            textvariable=self.func4Text, width=11,
            command=lambda i=4: self.callCustomFunc(i),
        )
        self.scriptbutton4.pack(padx=5, pady=5, side=LEFT)

        self.func5Text = StringVar()
        self.func5Text.set("Func 5")
        self.scriptbutton5 = ttk.Button(scriptframe,
            textvariable=self.func5Text, width=11,
            command=lambda i=5: self.callCustomFunc(i),
        )
        self.scriptbutton5.pack(padx=5, pady=5, side=LEFT)                              

        # terminal commands grid section --------------------------------------

        mainframe3 = ttk.Frame(self)
        mainframe3.grid(row=2, column=0, padx=0, pady=0, sticky='nsew')

        terminalfuncframe = ttk.LabelFrame(mainframe3, text="Terminal Functions",)
        terminalfuncframe.grid(row=0, column=0, padx=8, pady=8, sticky='nsew')

        self.colorlabel2 = ttk.Label(terminalfuncframe, width=3, text="")
        self.colorlabel2.pack(padx=5, pady=5, side=LEFT)
        self.colorlabel2.config(background=self.colorList[0])  

        startbutton = ttk.Button(
            terminalfuncframe,
            text="Run",
            width=13,
            command=lambda i=1: self.runstopFunction(i)
        )
        startbutton.pack(padx=5, pady=5, side=LEFT)

        stopbutton = ttk.Button(
            terminalfuncframe,
            text="Stop",
            width=13,
            command=lambda i=2: self.runstopFunction(i),
        )
        stopbutton.pack(padx=5, pady=5, side=LEFT)

        clearbutton = ttk.Button(
            terminalfuncframe, 
            text="Clear", 
            width=13, 
            command=lambda: self.clearFunction()
        )
        clearbutton.pack(padx=5, pady=5, side=LEFT) 

        bytecountcheckbox = ttk.Checkbutton(
            terminalfuncframe, 
            text="Show Bytecount",
            variable=self.showbytecount)

        bytecountcheckbox.pack(padx=5, pady=5, side=LEFT)

        logmodecheckbox = ttk.Checkbutton(
            terminalfuncframe, 
            text="Log Mode",
            variable=self.logmodeactive)

        logmodecheckbox.pack(padx=5, pady=5, side=LEFT)      

        spacerlabel = ttk.Label(terminalfuncframe, text="")
        spacerlabel.pack(padx=104, pady=5, side=LEFT)        

        self.linelabel = ttk.Label(terminalfuncframe, text="000000")
        self.linelabel.config(font=("consolas", 12))
        self.linelabel.pack(padx=5, pady=5, side=LEFT) 

        self.filterbutton = ttk.Button(
            terminalfuncframe, 
            text="Filter", 
            width=13, 
            command=lambda: self.filterWindow()
        )
        self.filterbutton.pack(padx=5, pady=5, side=RIGHT)
        self.filterbutton.config(state="normal")             

        # terminal grid section ----------------------------------------------

        mainframe4 = ttk.Frame(self)
        mainframe4.grid(row=3, column=0, padx=5, pady=5, sticky='nsew')        

        self.terminalbox = Text(mainframe4, width=127, height=31)
        self.terminalbox.config(font=("consolas", 10), undo=True, wrap="word")
        self.terminalbox.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.terminalbox.bind("<ButtonRelease-3>", self.rClicker, add="")

        terminalscrollb = ttk.Scrollbar(mainframe4, command=self.terminalbox.yview)
        terminalscrollb.grid(row=0, column=1, sticky="nsew")
        self.terminalbox["yscrollcommand"] = terminalscrollb.set

        self.master.bind("<Alt-c>", self.clearFunction)

    # class methods ---------------------------------------------------

    def launchScriptEditor(self):
        """
            Opens the script file for editing in the native editor
            on all operating systems
        """
        try:
            fileToEdit = "{}/{}.py".format(self.path, self.scriptName)
            if os.path.isfile(fileToEdit) :
                runningOn = platform.system()
                if runningOn == 'Darwin':
                    os.system("open " + shlex.quote(fileToEdit))
                elif runningOn == 'Windows':
                    os.system("start " + fileToEdit)
                elif runningOn == 'Linux':
                    os.system("xdg-open " + shlex.quote(fileToEdit))
                else:
                    msg = "Unknown OS!"
                    self.terminalFunction("ER", msg)
        except:
            msg = "No Script found!"
            self.terminalFunction("ER", msg)

    def reloadScript(self):
        """ function to reload a script when changed """

        importlib.reload(self.devscript)
        try:
            self.func1Text.set(self.devscript.funcName[0])
            self.func2Text.set(self.devscript.funcName[1])
            self.func3Text.set(self.devscript.funcName[2])
            self.func4Text.set(self.devscript.funcName[3])
            self.func5Text.set(self.devscript.funcName[4])
        except:
            msg = "Script import: Problem with Custom Function names 'funcName'"
            self.terminalFunction("ER", msg)
            
        msg = "Script has been reloaded"
        self.terminalFunction("--", msg)

    def browseFunction(self):
        """ pressed on the browse button """

        if self.portopen:
            msg = "Please close the open port first"
            self.terminalFunction("--", msg)
        
        else:
            fname = filedialog.askopenfilename(
                filetypes=(
                    ("Sim files", "*.json"),
                    ("All files", "*.*"),
                )
            )
            
            self.fname = fname
            path = os.path.dirname(os.path.abspath(fname))
            scriptName = os.path.basename(fname)[:-5]
            self.scriptName = scriptName
            self.path = path

            if fname:
                try:
                    msg = "Loading {}".format(fname)
                    self.terminalFunction("--", msg)
                except:
                    print("Failed to read file\n'%s'" % fname)

            """ Open the simulation json file """
            try:
                with open(fname) as data_file:
                    data = json.load(data_file)

                    loadedManufacturer = ""
                    loadedModel = ""
                    loadedPort = 0
                    loadedDelay = ""

                    if data:
                        loadedManufacturer = data[0]["Manufacturer"]
                        loadedModel = data[1]["Model"]
                        loadedPort = data[4]["Port"]
                        loadedDelay = data[5]["Delay"]

                        self.portentry.delete(0, END)
                        self.portentry.insert(0, loadedPort)
                        self.filelabel.config(text="{} - {}".format(loadedManufacturer, loadedModel))

                        msg = "{} - {} loaded with a Response Delay of {}s".format(
                            loadedManufacturer, loadedModel, loadedDelay
                        )
                        self.terminalFunction("--", msg)
                        self.runstopFunction(1)

                        if data[6]["Script"]:  # If a script is specified then also open that
                            msg = "Importing Script file: {}.py".format(scriptName)
                            self.terminalFunction("--", msg)
                            sys.path.append("{}".format(path))
                            try:
                                self.devscript = __import__(scriptName)
                            except Exception as e:
                                msg = "Script import failed: {}.py".format(e)
                                self.terminalFunction("ER", msg)
                            try:
                                self.func1Text.set(self.devscript.funcName[0])
                                self.func2Text.set(self.devscript.funcName[1])
                                self.func3Text.set(self.devscript.funcName[2])
                                self.func4Text.set(self.devscript.funcName[3])
                                self.func5Text.set(self.devscript.funcName[4])
                            except:
                                msg = "Script import: Problem with Custom Function names 'funcName'"
                                self.terminalFunction("ER", msg)
                        else:
                            self.devscript = None
                            self.func1Text.set("Func 1")
                            self.func2Text.set("Func 2")
                            self.func3Text.set("Func 3")
                            self.func4Text.set("Func 4")
                            self.func5Text.set("Func 5")

                        self.updateCommandsList(data)

            except Exception as e:
                print("Error opening sim file:", e) 

    def reloadJSON(self):
        """ pressed on the reload JSON button """

        if self.fname:
            try:
                msg = "Reloading JSON commands from {}".format(self.fname)
                self.terminalFunction("--", msg)
            except:
                print("Failed to read file\n'%s'" % self.fname)

            """ Open the simulation json file """
            try:
                with open(self.fname) as data_file:
                    data = json.load(data_file)

                    if data:
                        self.updateCommandsList(data)

            except Exception as e:        
                print("Error opening sim file:", e) 

    def updateCommandsList(self, data):

        self.commandsList = data

        for idx,cmd in enumerate(self.commandsList[7]): # converts all query and response loaded to bytes
            self.commandsList[7][idx]['Query'] = cmd['Query'].encode("latin-1").decode("unicode_escape").encode("latin-1")
            self.commandsList[7][idx]['Response'] = cmd['Response'].encode("latin-1").decode("unicode_escape").encode("latin-1")                                 

    def disconnectFunction(self):
        """ pressed on the disconnect button """

        app.mySocket.close()

    def sendentry_click(self, event):
        """ pressed on the manual send button """

        if self.sendentry.get() == "Replace this with ASCII or HEX bytes with prefix \\x":
            event.widget.delete(0, END)

    def sendFunction(self):
        """ sends a custom string defined in the code entry field """

        if self.sendentry.get() != "Replace this with ASCII or HEX bytes with prefix \\x":
            if app.mySocket:
                sendbyte = ast.literal_eval(f'b"{self.sendentry.get()}"')
                self.terminalFunction("OU", sendbyte)
                app.mySocket.write(sendbyte)
            else:
                msg = "No TCP connection detected"
                self.terminalFunction("--", msg)            

    def callCustomFunc(self, func):
        """ sends a custom data function """

        byteresponse = None
        
        if self.devscript:
            try:
                byteresponse = self.devscript.customFunc(func)
            except Exception as e:
                print('Exception occured in customFunc', e)            

            if byteresponse and self.mySocket:
                byteresponsesend = (byteresponse.encode("latin-1").decode("unicode_escape").encode("latin-1"))
                if "$$$" in byteresponse:
                    self.terminalFunction("FB", byteresponsesend[3:])    
                else:
                    self.terminalFunction("OU", byteresponsesend)
                    self.mySocket.write(byteresponsesend)
            else:
                msg = "No TCP connection detected"
                self.terminalFunction("--", msg)                           
        else:
            msg = "No script functions are loaded"
            self.terminalFunction("--", msg)                      

    def terminalFunction(self, direction, data):
        """ printing to the terminal window """

        if self.terminalrunning:
            msgdir = str(direction)
            now = datetime.datetime.now()
            msgnow = str(now.strftime("%H:%M:%S.%f")[:-3])
            msglen = len(data)
            msgdata = str(data)

            if direction == "--" or direction == 'ER':  # info or error lines
                color = 0
                msg = "{} | {} | {}\n".format(msgdir, msgnow, msgdata)
                self.terminalbox.tag_config(
                    str(self.colorList[color]), foreground=self.colorList[color]
                )
                self.terminalbox.insert(END, msg, str(self.colorList[color]))
                self.terminalbox.see(END)

            else:  # lines for incoming or outgoing data
                if direction == "IN":
                    color = 3                    
                else:
                    color = 4
                if app.showbytecount.get() == 0:
                    msg = "{} | {} | {}\n".format(msgdir, msgnow, msgdata)
                else:
                    msg = "{} | {} | {} | {}\n".format(msgdir, msgnow, msgdata, msglen)

                self.terminalbox.tag_config(str(self.colorList[color]), foreground=self.colorList[color])
                self.terminalbox.insert(END, msg, str(self.colorList[color]))
                self.terminalbox.see(END)

        self.terminallengthFunction()

    def terminallengthFunction(self):
        """ displays the total number of lines in the terminal """

        self.linelabel.config(
            text="{:06d}".format(
                int(self.terminalbox.index("end-1c").split(".")[0]) - 1
            )
        )

    def runstopFunction(self, index):
        """ starts/stops/clears the terminal box """

        if index == 1:
            self.terminalrunning = True
            self.colorlabel2.config(background=app.colorList[1])
        else:
            self.terminalrunning = False
            self.colorlabel2.config(background=app.colorList[0])

        self.terminallengthFunction()

    def clearFunction(self):
        """ clears the terminal box """

        self.terminalbox.delete(1.0, END)
        self.terminallengthFunction()

    def rClicker(self, e):
        """ right click context menu for all Tk Entry and Text widgets"""

        try:

            def rClick_All(apnd=0):
                e.widget.event_generate("<Control-a>")

            def rClick_Copy(apnd=0):
                e.widget.event_generate("<Control-c>")

            def rClick_Cut():
                e.widget.event_generate("<Control-x>")

            e.widget.focus()

            nclst = [
                (" Select All", rClick_All),
                (" Cut", rClick_Cut),
                (" Copy", rClick_Copy),
            ]

            rmenu = Menu(None, tearoff=0, takefocus=0)

            for (txt, cmd) in nclst:
                rmenu.add_command(label=txt, command=cmd)

            rmenu.tk_popup(e.x_root + 40, e.y_root + 10, entry="0")
        except TclError:
            print(" - rClick menu, something wrong")
        return "break"

    def rClickbinder(self, r):  # TODO: unused function
        """ binder for the right click menu """

        try:
            for b in ["Text", "Entry", "Listbox", "Label"]:  #
                r.bind_class(b, sequence="<Button-3>", func=self.rClicker, add="")
        except TclError:
            print(" - rClickbinder, something wrong")

    def filterWindow(self):
        """ opens a new filter window """

        self.filterbutton.config(state="disabled")

        def on_filterclosing():
            """ kills the filter window """

            self.filterbutton.config(state="normal")
            filterWindow.destroy()

        filterWindow = Toplevel()
        filterWindow.wm_title("Filter")
        filterWindow.pack_propagate(True)
        filterWindow.protocol("WM_DELETE_WINDOW", on_filterclosing)

        functionframe = ttk.LabelFrame(filterWindow, text="Filter Setup")
        functionframe.pack(fill=BOTH, padx=5, pady=5, side=TOP)

        resetfilterbutton = ttk.Button(
            functionframe, text="Reset", width=10, command=self.resetfilterFunction
        )
        resetfilterbutton.pack(padx=5, pady=5, side=LEFT)

        self.filterentry1 = ttk.Entry(functionframe, width=49)
        self.filterentry1.insert(0, "")
        self.filterentry1.pack(padx=5, pady=5, side=LEFT)

        self.filtervar = StringVar()
        filteroptions = ["AND", "OR"]
        self.filterword = ttk.OptionMenu(
            functionframe, self.filtervar, filteroptions[0], *filteroptions
        )
        self.filterword.config(width=7)
        self.filterword.pack(padx=5, pady=5, side=LEFT)

        self.filterentry2 = ttk.Entry(functionframe, width=49)
        self.filterentry2.insert(0, "")
        self.filterentry2.pack(padx=5, pady=5, side=LEFT)

        refreshbutton = ttk.Button(
            functionframe, text="Apply", width=10, command=self.refreshFunction
        )
        refreshbutton.pack(padx=5, pady=5, side=LEFT)

        filterframe = ttk.LabelFrame(filterWindow, text="Filtered Terminal")
        filterframe.pack(fill=BOTH, padx=5, pady=5, side=BOTTOM)

        self.filterbox = Text(filterframe, width=120, height=20)
        self.filterbox.config(font=("consolas", 10), undo=True, wrap="word")
        self.filterbox.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.filterbox.bind("<Button-3>", self.rClicker, add="")

        filterscrollb = ttk.Scrollbar(filterframe, command=self.filterbox.yview)
        filterscrollb.grid(row=0, column=1, sticky="nsew")
        self.filterbox["yscrollcommand"] = filterscrollb.set

        filterWindow.resizable(width=False, height=False)

        self.refreshFunction()   

    def resetfilterFunction(self):
        """ clears the filter entry field """

        self.filterentry1.delete(0, END)
        self.filterentry2.delete(0, END)
        self.filtervar.set("AND")
        self.refreshFunction()

    def refreshFunction(self):
        """ refresh the filter box """

        self.filterbox.delete(1.0, END)

        filterword1 = self.filterentry1.get()
        filterword2 = self.filterentry2.get()

        if len(filterword1) > 0 and len(filterword2) == 0:
            for line in self.terminalbox.get("1.0", "end-1c").splitlines():
                if filterword1 in line:
                    self.filterbox.insert(END, "{}\n".format(line))
        elif len(filterword1) > 0 and len(filterword2) > 0:
            for line in self.terminalbox.get("1.0", "end-1c").splitlines():
                if self.filtervar.get() == "AND":
                    if filterword1 in line and filterword2 in line:
                        self.filterbox.insert(END, "{}\n".format(line))
                elif self.filtervar.get() == "OR":
                    if filterword1 in line or filterword2 in line:
                        self.filterbox.insert(END, "{}\n".format(line))
        else:
            for line in self.terminalbox.get("1.0", "end-1c").splitlines():
                self.filterbox.insert(END, "{}\n".format(line))

    def jsoneditorWindow(self):
        """ opens a new JSON editor window """
         
        def on_jsoneditorclosing():
            """ kills the JSON editor window """

            jsoneditorWindow.destroy() 

        jsoneditorWindow = Toplevel()
        jsoneditorWindow.geometry("800x602+{}+{}".format(root.winfo_rootx()+57, root.winfo_rooty()+15))
        jsoneditorWindow.wm_title("JSON Editor")
        jsoneditorWindow.resizable(width=False, height=False)
        jsoneditorWindow.pack_propagate(True)
        jsoneditorWindow.protocol("WM_DELETE_WINDOW", on_jsoneditorclosing)     
        jsoneditorWindow.attributes('-topmost', True)  

        self.outfileName = str()
        self.entryframes = list()
        self.commandlist = list()
        self.querylist = list()
        self.responselist = list()                      

        def spinnerFunction(mode):
            """ updates spinner """

            if int(spinnerbox.get()) > len(self.entryframes):
                appendCommands()
            
            elif int(spinnerbox.get()) < len(self.entryframes):
                removeCommands()       

            if mode == 'new':
                self.commandlist[0].insert(0, 'ON_CONNECT')
                self.querylist[0].insert(0, 'ON_CONNECT')
                self.responselist[0].insert(0, 'Device is connected')                         

        def appendCommands():
            """ adds new command fields """

            entryframe = Frame(scrollframe.interior)        
            entryframe.pack(fill=BOTH)
            self.entryframes.append(entryframe)

            commandentry = ttk.Entry(entryframe, width=35)
            commandentry.config(font=("consolas", 10))
            commandentry.pack(side=LEFT, padx=5, pady=5, fill=X, expand=1)
            self.commandlist.append(commandentry)

            queryentry = ttk.Entry(entryframe, width=35)
            queryentry.config(font=("consolas", 10))
            queryentry.pack(side=LEFT, padx=5, pady=5, fill=X, expand=1)
            self.querylist.append(queryentry)

            responseentry = ttk.Entry(entryframe, width=35)
            responseentry.config(font=("consolas", 10))
            responseentry.pack(side=LEFT, padx=5, pady=5, fill=X, expand=1)
            self.responselist.append(responseentry) 
        
        def removeCommands():
            """ removes the last command fields """
            
            self.entryframes[-1].destroy()
            del self.entryframes[-1]
            del self.commandlist[-1]
            del self.querylist[-1]
            del self.responselist[-1]

        def newFile():
            """ clears all fields """
            
            fileentry.delete(0, END)
            manufacturerentry.delete(0, END)
            modelentry.delete(0, END)
            categoryentry.delete(0, END)
            versionentry.delete(0, END)
            jsonportentry.delete(0, END)
            delayentry.delete(0, END)
            delayentry.insert(0, 0.1)
            scriptbool.set(False)
            
            versionentry.insert(0, '1_0_0_0')
            spinnerbox.set('1')

            self.commandlist[0].delete(0, END)
            self.querylist[0].delete(0, END)
            self.responselist[0].delete(0, END)            
            self.commandlist[0].insert(0, 'ON_CONNECT')
            self.querylist[0].insert(0, 'ON_CONNECT')
            self.responselist[0].insert(0, 'Device is connected')

            for idx,entry in enumerate(self.entryframes):
                if idx > 0:
                    entry.destroy()  

            while len(self.entryframes) > 1:
                self.entryframes = self.entryframes[:-1]
                self.commandlist = self.commandlist[:-1]
                self.querylist = self.querylist[:-1]
                self.responselist = self.responselist[:-1]

        def openFile(idx):
            """ opens existing file """

            root.wm_attributes('-topmost', 1)
            if idx == 1:
                fname = filedialog.askopenfilename(filetypes=(("Sim files", "*.json"), ("All files", "*.*") ))
            else:
                fname = self.fname

            """ Open the simulation json file """
            try:
                root.wm_attributes('-topmost', 0)
                with open(fname) as data_file:    
                    data = json.load(data_file)

                    if data:
                        newFile()   
                        versionentry.delete(0, END)
                        delayentry.delete(0, END)
                        self.commandlist[0].delete(0, END)
                        self.querylist[0].delete(0, END)
                        self.responselist[0].delete(0, END)                                                      
                        
                        fileentry.insert(0, str(fname))
                        manufacturerentry.insert(0, str(data[0]['Manufacturer']))
                        modelentry.insert(0, str(data[1]['Model']))
                        categoryentry.insert(0, str(data[2]['Category']))
                        versionentry.insert(0, str(data[3]['Version']))
                        jsonportentry.insert(0, int(data[4]['Port']))
                        delayentry.insert(0, float(data[5]['Delay']))
                        scriptbool.set(data[6]['Script'])   
                        spinnerbox.set(str(len(data[7])))

                        for idx,data in enumerate(data[7]):
                            cmd = data['Description']
                            que = data['Query'].encode('unicode-escape').decode()
                            res = data['Response'].encode('unicode-escape').decode()
                            
                            if idx == 0:
                                self.commandlist[0].insert(0, cmd)
                                self.querylist[0].insert(0, que.replace(r'\\x', r'\x'))
                                self.responselist[0].insert(0, res.replace(r'\\x', r'\x'))                          
                            else:
                                appendCommands()
                                self.commandlist[idx].insert(0, cmd)
                                self.querylist[idx].insert(0, que.replace(r'\\x', r'\x'))
                                self.responselist[idx].insert(0, res.replace(r'\\x', r'\x'))                          

            except Exception as e:
                print('Error opening sim file:',e)
                root.wm_attributes('-topmost', 0)                 

        def saveFile():
            """ saves current file """

            if manufacturerentry.get() and modelentry.get() and categoryentry.get() and jsonportentry.get() and self.commandlist[0].get()\
                and self.querylist[0].get():
               
                manu = str(manufacturerentry.get())[:4].lower().replace(" ", "")
                mode = str(modelentry.get())[:6].lower().replace(" ", "")
                vers = str(versionentry.get())                
                self.outfileName = '{}_{}_{}.json'.format(manu, mode, vers)
                
                root.wm_attributes('-topmost', 1)
                outfile = filedialog.asksaveasfile(mode='w', initialfile=self.outfileName, title="Save the file", filetypes=(("json files","*.json"),("all files","*.*")))
                
                if outfile:
                    data = []
                    data.append({"Manufacturer":str(manufacturerentry.get())})
                    data.append({"Model":str(modelentry.get())})
                    data.append({"Category":str(categoryentry.get())})
                    data.append({"Version":str(versionentry.get())})
                    data.append({"Port":int(jsonportentry.get())})
                    data.append({"Delay":float(delayentry.get())})
                    data.append({"Script":bool(scriptbool.get())})
                    data.append([])

                    for idx, _ in enumerate(self.entryframes):                  
                        cmd = str(self.commandlist[idx].get())
                        que = str(self.querylist[idx].get()).encode('latin-1').decode()
                        res = str(self.responselist[idx].get()).encode('latin-1').decode()
                        data[7].append({"Description":cmd, "Query":que.replace(r'\x', r'\\x'), "Response":res.replace(r'\x', r'\\x')})                

                    outfile.write(json.dumps(data, sort_keys=True, indent=4).encode('latin-1').decode('unicode-escape'))
                    outfile.close()
                    root.wm_attributes('-topmost', 0)
            else:
                root.wm_attributes('-topmost', 1)
                messagebox.showerror("Cannot Save", "Please enter all fields!") 
                root.wm_attributes('-topmost', 0)
  
        jsonmenu = Menu(jsoneditorWindow)
        jsoneditorWindow.config(menu=jsonmenu)
        
        filemenu = Menu(jsonmenu, tearoff=0)
        jsonmenu.add_cascade(label="File", menu=filemenu)
        filemenu.add_command(label="New File", command=newFile)
        filemenu.add_separator()
        filemenu.add_command(label="Open Existing", command=lambda i=1: openFile(i))
        filemenu.add_command(label="Save To Disk", command=saveFile)
        filemenu.add_separator()
        filemenu.add_command(label="Exit Editor", command=on_jsoneditorclosing) 

        fileframe = Frame(jsoneditorWindow)        
        fileframe.pack(fill=BOTH)
        filelabel = ttk.Label(fileframe, width=18, text='Filename')
        filelabel.pack(side=LEFT, padx=5, pady=5)
        fileentry = ttk.Entry(fileframe, width=75)
        fileentry.pack(side=LEFT, padx=5, pady=5)

        manufacturerframe = Frame(jsoneditorWindow)        
        manufacturerframe.pack(fill=BOTH)
        manufacturerlabel = ttk.Label(manufacturerframe, width=18, text='Manufacturer')
        manufacturerlabel.pack(side=LEFT, padx=5, pady=5)
        manufacturerentry = ttk.Entry(manufacturerframe, width=50)
        manufacturerentry.pack(side=LEFT, padx=5, pady=5) 

        modelframe = Frame(jsoneditorWindow)        
        modelframe.pack(fill=BOTH)        
        modellabel = ttk.Label(modelframe, width=18, text='Model')
        modellabel.pack(side=LEFT, padx=5, pady=5)
        modelentry = ttk.Entry(modelframe, width=50)
        modelentry.pack(side=LEFT, padx=5, pady=5)            

        categoryframe = Frame(jsoneditorWindow)        
        categoryframe.pack(fill=BOTH)
        categorylabel = ttk.Label(categoryframe, width=18, text='Category')
        categorylabel.pack(side=LEFT, padx=5, pady=5)
        categoryentry = ttk.Entry(categoryframe, width=50)
        categoryentry.pack(side=LEFT, padx=5, pady=5) 

        versionframe = Frame(jsoneditorWindow)        
        versionframe.pack(fill=BOTH)        
        versionlabel = ttk.Label(versionframe, width=18, text='File Version')
        versionlabel.pack(side=LEFT, padx=5, pady=5)
        versionentry = ttk.Entry(versionframe, width=10)
        versionentry.insert(0, '1_0_0_0')
        versionentry.pack(side=LEFT, padx=5, pady=5, fill=X) 

        portframe = Frame(jsoneditorWindow)        
        portframe.pack(fill=BOTH)        
        portlabel = ttk.Label(portframe, width=18, text='TCP Port')
        portlabel.pack(side=LEFT, padx=5, pady=5)
        jsonportentry = ttk.Entry(portframe, width=10)
        jsonportentry.pack(side=LEFT, padx=5, pady=5, fill=X)

        delayframe = Frame(jsoneditorWindow)        
        delayframe.pack(fill=BOTH)
        delaylabel = ttk.Label(delayframe, width=18, text='Response Delay')
        delaylabel.pack(side=LEFT, padx=5, pady=5)
        delayentry = ttk.Entry(delayframe, width=10)
        delayentry.insert(0, '0.1')
        delayentry.pack(side=LEFT, padx=5, pady=5, fill=X) 

        scriptframe = Frame(jsoneditorWindow)        
        scriptframe.pack(fill=BOTH)        
        scriptlabel = ttk.Label(scriptframe, width=18, text='Script?')
        scriptlabel.pack(side=LEFT, padx=5, pady=5)
        scriptbool = IntVar()
        scriptentry = ttk.Checkbutton(scriptframe, variable=scriptbool)
        scriptentry.pack(side=LEFT, pady=5) 

        spinnerframe = Frame(jsoneditorWindow)        
        spinnerframe.pack(fill=BOTH)
        spinnerlabel = ttk.Label(spinnerframe, width=18, text='# Commands')
        spinnerlabel.pack(side=LEFT, padx=5, pady=5) 
        spinnerbox = ttk.Spinbox(spinnerframe, width=5, from_=1, to=20, command=lambda: spinnerFunction(None))
        spinnerbox.set('1')
        spinnerbox.pack(side=LEFT, padx=5, pady=5)            

        commandsframe = Frame(jsoneditorWindow)        
        commandsframe.pack(fill=BOTH)
        commandlabel = ttk.Label(commandsframe, text='Description')
        commandlabel.pack(side=LEFT, padx=5, pady=5, expand=1)
        querylabel = ttk.Label(commandsframe, text='Query')
        querylabel.pack(side=LEFT, padx=5, pady=5, expand=1)
        responselabel = ttk.Label(commandsframe, text='Response')
        responselabel.pack(side=LEFT, padx=5, pady=5, expand=1)  

        scrollframe = VerticalScrolledFrame(jsoneditorWindow)
        scrollframe.pack()
        scrolllabel = ttk.Label(jsoneditorWindow, text="More than 8 JSON commands will activate the scrollbar")
        scrolllabel.pack(pady=5)        

        spinnerFunction('new')

        if self.fname:
            openFile(2)

    def asciihexWindow(self):
        """ opens a new ASCII HEX window """
         
        def on_asciihexclosing():
            """ kills the ASCII HEX window """

            asciihexWindow.destroy()

        def asciihexFunction():
            hexvar = "".join("{:02x}".format(ord(c)) for c in asciientry.get())
            hexoutput.delete(0, END)
            hexoutput.insert(0, hexvar)   

        def hexasciiFunction():
            for char in hexentry.get():
                if char in ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F','a','b','c','d','e','f']:
                    if len(hexentry.get()) in range(2,200,2):
                        try:
                            asciivar = binascii.unhexlify(hexentry.get())
                            asciioutput.delete(0, END)
                            asciioutput.insert(0, asciivar)
                        except:
                            pass
                    else:
                        asciioutput.delete(0, END)
                        asciioutput.insert(0, 'Length Error')                        
                else:
                    asciioutput.delete(0, END)
                    asciioutput.insert(0, 'Character Error')

        asciihexWindow = Toplevel()
        asciihexWindow.geometry("+{}+{}".format(root.winfo_rootx()+262, root.winfo_rooty()+245))
        asciihexWindow.wm_title("ASCII - HEX Converter")
        asciihexWindow.resizable(width=False, height=False)
        asciihexWindow.pack_propagate(True)
        asciihexWindow.protocol("WM_DELETE_WINDOW", on_asciihexclosing)

        convframe1 = ttk.LabelFrame(asciihexWindow, text="ASCII to HEX",)
        convframe1.grid(row=0, column=0, padx=8, pady=8, sticky='nsew')       
        asciientry = ttk.Entry(convframe1, width=20, justify='center')
        asciientry.pack(padx=5, pady=5, side=LEFT) 
        hexoutput = ttk.Entry(convframe1, width=20, justify='center')
        hexoutput.pack(padx=5, pady=5, side=LEFT) 
        convbutton1 = ttk.Button(convframe1,
            text="Convert", width=13,
            command=lambda: asciihexFunction(),
        )
        convbutton1.pack(padx=5, pady=5, side=LEFT)       

        convframe2 = ttk.LabelFrame(asciihexWindow, text="HEX to ASCII",)
        convframe2.grid(row=1, column=0, padx=8, pady=8, sticky='nsew')       
        hexentry = ttk.Entry(convframe2, width=20, justify='center')
        hexentry.pack(padx=5, pady=5, side=LEFT) 
        asciioutput = ttk.Entry(convframe2, width=20, justify='center')
        asciioutput.pack(padx=5, pady=5, side=LEFT) 
        convbutton2 = ttk.Button(convframe2,
            text="Convert", width=13,
            command=lambda: hexasciiFunction(),
        )
        convbutton2.pack(padx=5, pady=5, side=LEFT)           

    def asciichartWindow(self, index):
        """ opens a new ASCII Chart window """
         
        def on_asciichartclosing():
            """ kills the ASCII Chart window """

            asciichartWindow.destroy()

        asciichartWindow = Toplevel()
        asciichartWindow.geometry("505x429+{}+{}".format(root.winfo_rootx()+203, root.winfo_rooty()+100))
        asciichartWindow.resizable(width=False, height=False)
        asciichartWindow.pack_propagate(True)
        asciichartWindow.protocol("WM_DELETE_WINDOW", on_asciichartclosing)  

        if index == 1:
            asciichartWindow.wm_title("Standard ASCII Chart")
            asciiimage = PhotoImage(file='assets/Standard-ASCII-Table1.gif')
        else:
            asciichartWindow.wm_title("Extended ASCII Chart")
            asciiimage = PhotoImage(file='assets/Extended-ASCII-Table2.gif')

        asciilabel = ttk.Label(asciichartWindow, image = asciiimage)
        asciilabel.place(x=0, y=0, relwidth=1, relheight=1)
        asciilabel.image = asciiimage   

    def howtoWindow(self):
        """ opens a new HowTo window """
         
        def on_howtoclosing():
            """ kills the HowTo window """

            howtoWindow.destroy()

        howtoWindow = Toplevel()
        howtoWindow.geometry("505x429+{}+{}".format(root.winfo_rootx()+205, root.winfo_rooty()+95))
        howtoWindow.wm_title("How to use PEA")
        howtoWindow.resizable(width=False, height=False)
        howtoWindow.pack_propagate(True)
        howtoWindow.protocol("WM_DELETE_WINDOW", on_howtoclosing) 
        
        howtoFrame = VerticalScrolledFrame(howtoWindow) 
        howtoFrame.pack(expand=1, fill=BOTH)
        
        howtomsg = '''How to use PEA

Here are the steps required to create a working
TCP emulator using PEA:

1) Obtain the protocol for the device you need to emulate
2) Establish the TCP Port number NOT lower than 1024
3) Open the JSON editor entering all the device details
4) To add a new command line increase the number of commands
5) Add a description, query & response. Use this format

    ascii: hello\\r\\n
    ascii and hex: hello\\x0a\\x0d
    hex: \\x35\\x75\\x0d\\x0a

This method allows simple protocols to be quickly and easily
created using JSON only. If you need more complex responses, such
as feedback from a switcher with changing values, then use an
associated python script to deal with more complex requirements.

To enable an associated script check the Script? box in the JSON
editor and then create (in the same folder) a .py file with the
same filename as the JSON file. This will be automatically loaded
if the checkbox is ticked.

If you have modified the JSON or Script file you need to use the
appropiate Reload menu option to update the emulator.

Be aware that the Reload JSON only reloads the TCP query commands
and not the connection details. If you change one of the other
details such as Port number, Script checkbox or the Delay you need
to use the Browse for Emulator JSON File menu option again.

Look at the example template JSON and PY Script for more details
on how to deal with received and send strings.'''

        howtoText = ttk.Label(howtoFrame.interior, text=howtomsg)
        howtoText.config(font=("consolas", 10))             
        howtoText.pack(padx=8, pady=8)

    def aboutWindow(self):
        """ opens a new About window """
         
        def on_aboutclosing():
            """ kills the About window """

            aboutWindow.destroy()

        aboutWindow = Toplevel()
        aboutWindow.geometry("402x305+{}+{}".format(root.winfo_rootx()+255, root.winfo_rooty()+155))
        aboutWindow.wm_title("About PEA")
        aboutWindow.resizable(width=False, height=False)
        aboutWindow.pack_propagate(True)
        aboutWindow.protocol("WM_DELETE_WINDOW", on_aboutclosing) 

        aboutCanvas = Canvas(aboutWindow, width=0, height=0)
        aboutCanvas.pack(expand=YES, fill=BOTH)
        pealogo = PhotoImage(file='assets/logo.gif')
        aboutCanvas.pealogo = pealogo
        aboutCanvas.create_image((10, 10), anchor='nw', image=pealogo)

        aboutmsg = """PEA: a python written tcp ethernet device emulator  \n
Version: 1.0.0
Python Version: 3.8.5\n
Github Repo: https://github.com/clydefrog76/pea\n
Programmers: Alexander Teusch
             Rupert Powell"""

        aboutCanvas.create_text(10, 150, anchor='nw', font=("Consolas", 10), text=aboutmsg)  

    def donationsWindow(self):
        """ opens a new Donations window """
         
        def on_donationsclosing():
            """ kills the Donations window """

            donationsWindow.destroy()

        donationsWindow = Toplevel()
        donationsWindow.geometry("510x580+{}+{}".format(root.winfo_rootx()+202, root.winfo_rooty()+19))
        donationsWindow.wm_title("Donations")
        donationsWindow.resizable(width=False, height=False)
        donationsWindow.pack_propagate(True)
        donationsWindow.protocol("WM_DELETE_WINDOW", on_donationsclosing)  

        donationsCanvas = Canvas(donationsWindow, width=0, height=0)
        donationsCanvas.pack(expand=YES, fill=BOTH)

        donationsmsg = """Although PEA is free, fully open-source and built with the community
in mind, we the developers still have spend dozends of hours in\ncreating and testing this tool.\n
If you like this great tool and you wish to support us and contribute
to future improvements, updates or even just some beer money, please
feel free to donate ANY amount you like, big or small to:"""

        donationsCanvas.create_text(15, 15, anchor='nw', font=("Consolas", 10), text=donationsmsg)     
        donationsCanvas.create_text(15, 150, anchor='nw', font=("Consolas", 10), text='PayPal:', fill='blue')
        donationsCanvas.create_text(85, 150, anchor='nw', font=("Consolas", 10), text='alexander.teusch@runbox.com')
        donationsCanvas.create_text(15, 175, anchor='nw', font=("Consolas", 10), text='Bitcoin:', fill='blue')
        bitcoin = PhotoImage(file='assets/bitcoin.gif')
        donationsCanvas.bitcoin = bitcoin
        donationsCanvas.create_image((85, 175), anchor='nw', image=bitcoin)

    # start of socket functions -----------------------------------------------------------------------------------------------                

    async def listenFunction(self):
        """ gets trigger from Open Port button or the file loader """

        if self.portopen == False:
            if self.commandsList and int(self.portentry.get()) >= 1024:
                self.portbutton.config(text="Close Port")
                self.portopen = True
                
                newport = int(self.portentry.get())
                self.port["listen"] = newport

                msg = "Port {} is open".format(newport)
                self.terminalFunction("--", msg)

                self.portentry.delete(0, END)
                self.portentry.insert(0, str(self.port["listen"]))
                self.portentry.config(state="disabled")   

                try:
                    self.loop = asyncio.get_running_loop()
                    self.sock = await self.loop.create_server(lambda: SocketServer(),'0.0.0.0', int(self.portentry.get()))
                except Exception as e:
                    print(e)                        

            else:
                msg = "Port not openend, please load a file first and check the Port is 1024 or higher!"
                self.terminalFunction("--", msg)

        elif self.portopen == True:
            msg = "Port is closed"
            self.terminalFunction("--", msg)  

            self.portentry.config(state="normal")
            self.portbutton.config(text="Open Port")
            self.port["listen"] = 0
            self.portopen = False      

            connection_close()
            self.sock.close()

class SocketServer(asyncio.Protocol):
    def connection_made(self, transport):
        self.socketdetails = transport.get_extra_info('sockname')
        app.port["connected"] = self.socketdetails[1]
        app.mySocket = transport 

        msg = "Client {} connected".format(self.socketdetails[0])
        app.colorlabel.config(background=app.colorList[1])
        app.terminalFunction("--", msg)
        app.disconnectbutton.config(state="active")

        if app.commandsList:
            if b'ON_CONNECT' in app.commandsList[7][0]["Query"]:
                app.terminalFunction("OU", app.commandsList[7][0]["Response"])
                try:
                    app.mySocket.write(app.commandsList[7][0]["Response"])
                except:
                    print('Error sending bytes')          

    def data_received(self, data):
        app.terminalFunction("IN", data) 

        self.idx = 0

        if app.commandsList:

            result = any(x["Query"] == data for self.idx, x in enumerate(app.commandsList[7]))

            if result:  # command found in query
                delay = float(app.commandsList[5]["Delay"])
                time.sleep(delay)
                app.terminalFunction("OU", app.commandsList[7][self.idx]["Response"])
                try:
                    app.mySocket.write(app.commandsList[7][self.idx]["Response"])
                except:
                    pass
            else:  # command not found in query, trying script

                if app.devscript:  # invoke the script (if there is one)
                    try:
                        byteresponse = app.devscript.rxscript(
                            app.mySocket, data
                        )
                    except Exception as e:
                        print('Exception occured in devscript', e)
                    try:
                        if byteresponse:
                            byteresponsesend = (
                                byteresponse.encode("latin-1")
                                .decode("unicode_escape")
                                .encode("latin-1")
                            )
                            app.mySocket.write(byteresponsesend)
                            app.terminalFunction("OU", byteresponsesend)
                        else:  # Nothing found in query or script
                            if app.logmodeactive.get() == 0:
                                byteresponse = "Error - no match found in query or script"
                                app.terminalFunction("ER", byteresponse)
                            try:
                                app.mySocket.write(bytes(byteresponse, "utf-8"))
                            except Exception as e:
                                print('Exception occured in sending', e)
                    except:
                        app.terminalFunction("ER", 'Script ERROR!')
                else:  # Nothing found in query
                    if app.logmodeactive.get() == 0:
                        byteresponse = "Error - no match found with query"
                        app.terminalFunction("ER", byteresponse)
                        app.mySocket.write(bytes(byteresponse, "utf-8"))
        else:
            app.terminalFunction(
                "--", "Error - no device emulator file has been loaded"
            )             

    def connection_lost(self, exc):
        msg = "Client {} disconnected".format(self.socketdetails[0])
        app.colorlabel.config(background=app.colorList[0])
        app.terminalFunction("--", msg)
        app.port["connected"] = 0
        app.disconnectbutton.config(state="disabled")

def connection_close():
    if app.mySocket:
        app.mySocket.close()
    app.mySocket = None
    app.port["connected"] = 0
    app.disconnectbutton.config(state="disabled")

class VerticalScrolledFrame(Frame):
    """A pure Tkinter scrollable frame that actually works!
    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    """

    def __init__(self, parent, *args, **kw):
        Frame.__init__(self, parent, *args, **kw)            

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = ttk.Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0, yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior, anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)        


async def main():
    await run_tk(root)


def on_closing():
    """ closes the main window and kills the proces / task """

    if messagebox.askokcancel("Exit PEA", "Do you want to quit?"):
        root.destroy()


root = Tk()
root.resizable(width=False, height=False)
root.wm_attributes('-topmost', 0)
root.protocol("WM_DELETE_WINDOW", on_closing)  # Trigger on plain closing the window
root.call("wm", "iconphoto", root._w, PhotoImage(file="assets/icon.png"))    
app = Window(root)

mystyle = ttk.Style()
if sys.platform.startswith('win'):
    mystyle.theme_use("vista")  # classic,default,clam,winnative,vista,xpnative,alt
else:
    mystyle.theme_use("default")

asyncio.run(main())
