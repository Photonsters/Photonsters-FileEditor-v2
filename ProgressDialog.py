from tkinter import Button, Tk, HORIZONTAL
from tkinter.ttk import Progressbar
import tkinter

class showProgress():
    progress=None
    cancel=None
    label=None

    def __init__(self,parent,title='progress',minVal=0,maxVal=100,autoShow=True,autoHide=True,cancelButton=True):
        self.parent=parent
        self.title=title
        self.minVal=minVal
        self.maxVal=maxVal
        self.autoHide=autoHide
        self.cancelButton=cancelButton
        if autoShow: self.show()

    def show(self):
        # Create child
        top = tkinter.Toplevel(self.parent)
        top.wm_title(self.title)   
        self.top=top
        # Remove min/max buttons for child
        top.resizable(False,False) # no resize in X and Y
        top.transient(self.parent) # remove max and min buttons for window
        # Redirect close button in window bar
        top.protocol('WM_DELETE_WINDOW', self.hide)
        # Populate child with widgets
        self.label=tkinter.Label(top,text="0%")
        self.label.grid(row=0,column=0,pady=12)
        self.progress = Progressbar(top, orient=HORIZONTAL,length=320,mode='determinate')
        self.progress.grid(row=1,column=0,padx=12,pady=0)
        self.cancel = Button(top, text='Cancel', command=self.hide)
        self.cancel.grid(row=3,column=0,pady=12)
        if not self.cancelButton: self.cancel["state"] = tkinter.DISABLED

        # Position child
        top.update()
        top.update_idletasks()

        # Center this child
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()

        cw = self.top.winfo_width()
        ch = self.top.winfo_height()
        cx = px+(pw-cw)/2
        cy = py+(ph-ch)/2
        geom = "+%d+%d" % (cx,cy)
        top.geometry(geom)        


    def hide(self):
        print ("Hide")
        self.top.destroy()

    oldVal=-1
    def setProgress(self,val):
        if val<self.minVal: val=self.minVal
        if val>self.maxVal: val=self.maxVal
        
        pval=0
        if val==self.maxVal:
            pval=100
        else:            
            pval=int(100*(val-self.minVal))/(self.maxVal-self.minVal)
        self.progress['value']=pval
        self.label['text']=str(pval)+"%"

        if val==self.maxVal:
            if self.autoHide:
                self.hide()
            else:
                self.label['text']="100%"
                self.cancel['text']='OK'
                self.cancel["state"] = tkinter.NORMAL
        
        if pval!=self.oldVal:
            self.oldVal=pval
            #print (val,str(pval)+"%")                
            self.label.update()
            self.label.update_idletasks()
            self.progress.update()
            self.progress.update_idletasks()
            self.top.update()
            self.top.update_idletasks()

    def setProgressPerc(self,val):
        if val<0: val=0
        if val>100: val=100
        
        self.progress['value']=val
        self.label['text']=str(val)+"%"

        if val==100:
            if self.autoHide:
                self.hide()
            else:
                self.label['text']="100%"
                self.cancel['text']='OK'
                self.cancel["state"] = tkinter.NORMAL
        
        if val!=self.oldVal:
            self.oldVal=val
            #print (val,str(val)+"%")                
            self.label.update()
            self.label.update_idletasks()
            self.progress.update()
            self.progress.update_idletasks()
            self.top.update()
            self.top.update_idletasks()

i=0
app=None
def runProgress():
    global root,app,i
    print ("Run Dialog")
    app = showProgress(root,"Progress", 0,200,True,False,False)
    updateProgress()

def updateProgress():
    global root,app,i
    app.setProgress(i)
    i=i+1
    if i<401:
        print (i)
        root.after(10,updateProgress)

if __name__ == '__main__':
    root=tkinter.Tk()
    root.geometry("%dx%d+0+0" % (640,480))
    root.title("Main Window")
    root.name="root"
    root.after(1000,runProgress)
    root.mainloop()
