
import tkinter as tk
from tkinter import ttk as ttk

class ResinDialog():
    infoPathEditor=None
    tree=None
    vals=None

    def __init__(self,parent,title='Select Resin'):
        print ("INIT")
        self.parent=parent
        self.title=title

    def show(self,):
        global tree
        print ("SHOW")

        # Create child
        top = tk.Toplevel(self.parent)
        top.wm_title(self.title)   
        self.top=top
        # Remove min/max buttons for child
        #top.resizable(False,False) # no resize in X and Y
        top.transient(self.parent) # remove max and min buttons for window
        # Redirect close button in window bar
        top.protocol('WM_DELETE_WINDOW', self.cancel)

        # Read CSV
        # First read settings from file
        # columns are Brand,Type,Layer,NormalExpTime,OffTime,BottomExp,BottomLayers
        ifile = open("resins.csv", "r",encoding="Latin-1") #Latin-1 handles special characters
        lines = ifile.readlines()
        headers=lines[0].split(";")
        data=lines[1:]
        resins = [tuple(line.strip().split(";")) for line in data]

        # set to system default monospace font
        style = ttk.Style()
        style.configure("mystyle.Treeview", highlightthickness=0, bd=0, font=('Calibri', 11)) # Modify the font of the body
        style.configure("mystyle.Treeview", font=('DejaVu Sans Mono', 10,'normal')) # Modify the font of the headings
        style.layout("mystyle.Treeview", [('mystyle.Treeview.treearea', {'sticky': 'nswe'})]) # Remove the borders        
 
        top.columnconfigure(0,weight=1)
        top.columnconfigure(1,weight=0)
        top.columnconfigure(2,weight=0)
        top.rowconfigure(0,weight=1)
        top.rowconfigure(1,weight=0)
        
        # Table
        frame=tk.Frame(top,bg='red')
        frame.grid(row=0,column=0,columnspan=3,padx=12,pady=(12,0))
        TableMargin = tk.Frame(frame, width=200)
        TableMargin.pack(side=tk.TOP)
        scrollbarx = tk.Scrollbar(TableMargin, orient=tk.HORIZONTAL)
        scrollbary = tk.Scrollbar(TableMargin, orient=tk.VERTICAL)
        tree = ttk.Treeview(TableMargin, 
                            columns=headers, 
                            height=200, 
                            selectmode="extended", 
                            yscrollcommand=scrollbary.set, xscrollcommand=scrollbarx.set,
                            style="mystyle.Treeview")
        scrollbary.config(command=tree.yview)
        scrollbary.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbarx.config(command=tree.xview)
        scrollbarx.pack(side=tk.BOTTOM, fill=tk.X)     

        for header in headers:
            tree.heading(header, text=header, anchor=tk.W)

        # Fill table
        for resin in resins:
            #print ("resin[0]",resin[0])
            tree.insert("", 0, values=(resin))

        # Set column widths
        colChars=[0]*len(headers)
        for resin in resins:
            for colnr,prop in enumerate(resin):
                colChars[colnr]=max(colChars[colnr],len(prop))

        tree.column('#0', stretch=tk.NO, minwidth=0, width=0)        
        for colnr in range(len(headers)):
            colname='#'+str(colnr+1)
            w=colChars[colnr]*8+16
            tree.column(colname, stretch=True, minwidth=40, width=w)
        tree.pack()#expand=True,fill=tk.BOTH)

        self.ok = tk.Button(top, text='Ok', command=self.apply)
        self.ok.grid(row=2,column=2,padx=12,pady=12)

        self.cancel = tk.Button(top, text='Cancel', command=self.cancel)
        self.cancel.grid(row=2,column=1,padx=12,pady=12)
 
        top.geometry("%dx%d+0+0" % (512,320))
        top.update()
        top.update_idletasks()

        top.grab_set()           # modal
        self.parent.wait_window(top) # why?
        return (self.vals)        

    def selectItem(self):
        curItemId = tree.focus()
        curItem = tree.item(curItemId)
        curVals = curItem['values']
        return curVals

    def cancel(self):
        print ("Hide")
        self.vals=None
        self.top.destroy()

    def apply(self):
        print ("Apply")
        self.vals=self.selectItem()
        self.top.destroy()

if __name__ == '__main__':
    root=tk.Tk()
    root.geometry("%dx%d+0+0" % (96,48))
    root.title("Root")
    root.name="root"
    def showDialog():
        showDialog=ResinDialog(root)
        ret=showDialog.show()
        print ("showPr",ret)
    root.after(100,showDialog)
    root.mainloop()
