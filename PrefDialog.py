
import tkinter
from tkinter import filedialog
from tkinter import ttk as ttk

class ShowPreferences():
    infoPathEditor=None

    def __init__(self,parent,title='preferences'):
        print ("INIT")
        self.parent=parent
        self.title=title

    def show(self,prefs=['new file...','%1',"top","bottom","left","top","right"]):
        print ("SHOW")
        self.retVar=prefs
        # Create child
        top = tkinter.Toplevel(self.parent)
        top.wm_title(self.title)   
        self.top=top
        # Remove min/max buttons for child
        #top.resizable(False,False) # no resize in X and Y
        top.transient(self.parent) # remove max and min buttons for window
        # Redirect close button in window bar
        top.protocol('WM_DELETE_WINDOW', self.cancel)
        # Populate child with widgets
        top.columnconfigure(0,weight=1)
        frame=tkinter.Frame(top)#,bg='red')
        frame.grid(column=0,row=0,sticky='nsew',padx=24,pady=24)

        # Editor
        eframe=tkinter.Frame(frame)#,bg='red')
        eframe.grid(column=0,row=0,sticky='nsew')
        eframe.columnconfigure(0,weight=1)
        eframe.columnconfigure(1,weight=2)
        eframe.columnconfigure(2,weight=1)

        self.catEditor=tkinter.Label(eframe,text="Editor",anchor='w',font=('Helvetica', 11, 'bold'))
        self.catEditor.grid(row=0,column=0,sticky='w')

        self.editorPath = tkinter.StringVar()
        self.editorPath.set(self.retVar[0])
        self.labelPathEditor=tkinter.Label(eframe,text="path",padx=16,anchor='w')
        self.labelPathEditor.grid(row=1,column=0,padx=12,sticky='w')
        self.infoPathEditor=tkinter.Entry(eframe,width=24,textvariable=self.editorPath)
        self.infoPathEditor.grid(row=1,column=1,padx=4,sticky='ew')
        self.cmdPathEditor=tkinter.Button(eframe,text='select',command=self.selectEditorExe)
        self.cmdPathEditor.grid(row=1,column=2,padx=4,pady=4,sticky='e')
        
        self.editorArgs=tkinter.StringVar()
        self.editorArgs.set(self.retVar[1])
        self.labelPathArgs=tkinter.Label(eframe,text="arguments",padx=16,anchor='w')
        self.labelPathArgs.grid(row=2,column=0,padx=12,sticky='w')
        self.entryPathArgs=tkinter.Entry(eframe,text="%1",textvariable=self.editorArgs)
        self.entryPathArgs.grid(row=2,columnspan=2,column=1,padx=4,sticky='ew')

        # Toolbar placement
        sep=ttk.Separator(frame,orient=tkinter.HORIZONTAL)
        sep.grid(column=0,row=1,columnspan=3,sticky="ew",padx=4,pady=8)
        tframe=tkinter.Frame(frame)#,bg='red')
        tframe.grid(column=0,row=2,sticky='nsew')
        self.catToolbars=tkinter.Label(tframe,text="Toolbars",anchor='w',font=('Helvetica', 11, 'bold'))
        self.catToolbars.grid(row=4,column=0,sticky='w')

        tframe.columnconfigure(0,weight=1)
        tframe.columnconfigure(1,weight=1)
        tframe.columnconfigure(2,weight=1)
        tframe.columnconfigure(3,weight=1)
        tframe.columnconfigure(4,weight=1)


        # Tab1
        self.catToolbars=tkinter.Label(tframe,text="Tab1",anchor='w',font=('Helvetica', 11, 'bold'))
        self.catToolbars.grid(row=5,column=1,columnspan=2,sticky='w')
        #self.label=tkinter.Label(tframe,text="Iconbar",anchor='w',font=('Helvetica', 11, 'normal'))
        #self.label.grid(row=6,column=1,sticky='w')
        self.label=tkinter.Label(tframe,text="Slider",anchor='w',font=('Helvetica', 11, 'normal'))
        self.label.grid(row=7,column=1,sticky='w')
        self.label=tkinter.Label(tframe,text="Infobar",anchor='w',font=('Helvetica', 11, 'normal'))
        self.label.grid(row=8,column=1,sticky='w')

        self.tab1=[tkinter.StringVar(),tkinter.StringVar(),tkinter.StringVar()]
        #self.combobox = ttk.Combobox(tframe, state="readonly",values=("left","right","bottom"),width=8, textvariable=self.tab1[0])
        #self.combobox.grid(row=6,column=2,sticky='w')
        self.combobox = ttk.Combobox(tframe, state="readonly",values=("left","right","bottom"),width=8, textvariable=self.tab1[1])
        self.combobox.grid(row=7,column=2,sticky='w')
        self.combobox = ttk.Combobox(tframe, state="readonly",values=("left","right","bottom"),width=8, textvariable=self.tab1[2])
        self.combobox.grid(row=8,column=2,sticky='w')

        self.tab1[0].set(self.retVar[2])
        self.tab1[1].set(self.retVar[3])
        self.tab1[2].set(self.retVar[4])

        # Tab2
        self.catToolbars=tkinter.Label(tframe,text="Tab2",anchor='w',font=('Helvetica', 11, 'bold'))
        self.catToolbars.grid(row=5,column=4,columnspan=2,sticky='w')
        #self.label=tkinter.Label(tframe,text="Iconbar",anchor='w',font=('Helvetica', 11, 'normal'))
        #self.label.grid(row=6,column=4,sticky='w')
        self.label=tkinter.Label(tframe,text="Slider",anchor='w',font=('Helvetica', 11, 'normal'))
        self.label.grid(row=7,column=4,sticky='w')

        self.tab2=[tkinter.StringVar(),tkinter.StringVar(),tkinter.StringVar()]
        #self.combobox = ttk.Combobox(tframe, state="readonly",values=("left","right","bottom"),width=8, textvariable=self.tab2[0])
        #self.combobox.grid(row=6,column=5,sticky='w')
        self.combobox = ttk.Combobox(tframe, state="readonly",values=("left","right","bottom"),width=8, textvariable=self.tab2[1])
        self.combobox.grid(row=7,column=5,sticky='w')

        self.tab2[0].set(self.retVar[5])
        self.tab2[1].set(self.retVar[6])

        # Set Buttons
        sep=ttk.Separator(frame,orient=tkinter.HORIZONTAL)
        sep.grid(column=0,row=3,columnspan=3,sticky="ew",padx=4,pady=8)

        self.ok = tkinter.Button(frame, text='Ok', command=self.apply)
        self.ok.grid(row=4,column=1,padx=12)
        self.cancel = tkinter.Button(frame, text='Cancel', command=self.cancel)
        self.cancel.grid(row=4,column=2,padx=4,sticky='e')

        #top.geometry("%dx%d+0+0" % (320,240))
        top.update()
        top.update_idletasks()

        top.grab_set()           # modal
        self.parent.wait_window(top) # why?
        return (self.retVar)
        
    def selectEditorExe(self):
        filename =  tkinter.filedialog.askopenfilename(initialdir = ".",title = "Select editor exe",filetypes = (("all files","*.*"),))
        if not filename: return
        self.infoPathEditor.delete(0, tkinter.END)
        self.infoPathEditor.insert(0, filename)            

    def cancel(self):
        print ("Hide")
        self.top.destroy()
    def apply(self):
        print ("Apply")
        self.retVar[0]=(self.editorPath.get())
        self.retVar[1]=(self.editorArgs.get())
        self.retVar[2]=(self.tab1[0].get())
        self.retVar[3]=(self.tab1[1].get())
        self.retVar[4]=(self.tab1[2].get())
        self.retVar[5]=(self.tab2[0].get())
        self.retVar[6]=(self.tab2[1].get())
        self.top.destroy()


if __name__ == '__main__':
    root=tkinter.Tk()
    root.geometry("%dx%d+0+0" % (96,48))
    root.title("Root")
    root.name="root"
    def showPref():
        showPref=ShowPreferences(root,"Preferences")
        ret=showPref.show(prefs=["nard2","%2","top","bottom","left","top","bottom"])
        print ("ret",ret)
    root.after(100,showPref)
    root.mainloop()
