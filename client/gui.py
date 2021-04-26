
# code references:
# https://realpython.com/python-gui-tkinter
# https://stackoverflow.com/questions/111155/how-do-i-handle-the-window-close-event-in-tkinter
# https://www.tutorialspoint.com/progressbar-widget-in-python-tkinter

import tkinter as tk
from tkinter import HORIZONTAL
from tkinter import filedialog as fd
from tkinter.ttk import Progressbar
from connections.mainConnection import MainConnection
import os
from config import SERVER_IP

connection = None

def connectionPrompt():
    mainWindow = tk.Tk()

    frm_ip = tk.Frame()

    lbl_ip = tk.Label(text='Choose FTP server IP:', master=frm_ip)
    lbl_ip.pack(fill=tk.Y, side=tk.LEFT)

    ent_ip = tk.Entry( master=frm_ip)
    ent_ip.pack(fill=tk.Y, side=tk.LEFT)

    frm_ip.pack(fill=tk.X)

    frm_conn = tk.Frame()
    lbl_conn = tk.Label(text='Choose FTP connection method:', master=frm_conn)
    lbl_conn.pack(fill=tk.Y, side=tk.LEFT)

    def connect():
        return MainConnection(server_ip=ent_ip.get())

    def showError(error):
        lbl_warning['text'] = error

    def chooseUDP():
        if ent_ip.get().strip():
            conn = connect()
            conn = conn.connectFTP('UDP')
            mainWindow.destroy()
            fileWindow(conn)
        else:
            showError("Empty IP")

    def chooseTCP():
        if ent_ip.get().strip():
            conn = connect()
            conn = conn.connectFTP('TCP')
            mainWindow.destroy()
            fileWindow(conn)
        else:
            showError("Empty IP")


    btn_tcp = tk.Button(
        text='TCP',
        master=frm_conn,
        command= chooseTCP
    )
    btn_tcp.pack(fill=tk.Y, side=tk.LEFT)
    btn_udp = tk.Button(
        text='UDP',
        master=frm_conn,
        command=chooseUDP
    )
    btn_udp.pack(fill=tk.Y, side=tk.LEFT)

    frm_conn.pack(fill=tk.X)

    lbl_warning = tk.Label(foreground='RED')
    lbl_warning.pack()
    mainWindow.mainloop()

import time
# contribution from https://www.geeksforgeeks.org/how-to-embed-matplotlib-charts-in-tkinter-gui/
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
NavigationToolbar2Tk)

def fileWindow(connection):
    fileList = connection.getFiles()


    window = tk.Tk()
    lbl_files = tk.Label(text='Files on Server')
    lbl_files.pack()

    frm_main = tk.Frame()
    frm_files = tk.Frame(master=frm_main)

    frm_plot = tk.Frame()
    frm_progress = tk.Frame( master=frm_main)
    lbl_progress = tk.Label(master=frm_progress)
    progressBar = Progressbar(frm_progress, orient=HORIZONTAL, length=200, mode='determinate')
    lbl_rate = tk.Label(master=frm_progress)

    X = []
    Y = []

    def progress(done, total, bitrate):
        global fileList

        fraction = total//30
        #update progress only if we move by a fraction of total
        if fraction ==0 or done%fraction == 0 or done == total:
            X.append(time.perf_counter_ns() / 1E9)
            Y.append(bitrate)
            progressBar['value'] = done * 1.0 / total * 100.0
            lbl_rate['text'] = f'{round(bitrate)} bits/s'
            if done == total:
                lbl_progress['text'] = "Finished"
                lbl_rate['text'] = f'Average {round(bitrate)} bits/s'
                fig = Figure(figsize=(5, 5),
                             dpi=100)
                fig.clear()
                plot1 = fig.add_subplot(111)
                fig.supylabel('Bitrate (bps)')
                fig.supxlabel('timestamp (s)')
                plot1.plot(X,Y)

                for child in frm_plot.children:
                    frm_plot.children[child].destroy()
                    break

                canvas = FigureCanvasTkAgg(fig,
                                           master=frm_plot)
                canvas.draw()
                X.clear()
                Y.clear()

                fileList = connection.getFiles()
                showFiles(fileList)


                # placing the canvas on the Tkinter window
                canvas.get_tk_widget().pack()
            window.update_idletasks()



    def showFiles(fileList):
        for i in range(len(fileList)):
            frm_files.columnconfigure(i, weight=1, minsize=75)
            frm_files.rowconfigure(i, weight=1, minsize=50)

            frame = tk.Frame(
                master=frm_files,
                borderwidth=1
            )
            frame.grid(row=i, column=0, padx=5, pady=5)

            label = tk.Label(master=frame, text=fileList[i]['file'])
            label.pack(padx=5, pady=5)

            frame = tk.Frame(
                master=frm_files,
                borderwidth=1
            )
            frame.grid(row=i, column=1, padx=5, pady=5)

            def download(i):

                lbl_progress['text'] = "Downloading "+ fileList[i]['file']
                window.update_idletasks()
                path = fd.askdirectory()
                if len(path)<2: return
                connection.downloadFile(fileList[i]['id'],path , log=progress)


            btn = tk.Button(
                master=frame,
                text='Download',
                command = lambda a=i: download(a)
            )
            btn.pack(padx=5, pady=5)

    showFiles(fileList)

    frm_main.pack(side=tk.LEFT)
    frm_files.pack()
    frm_plot.pack(side =tk.RIGHT)
    lbl_progress.pack(fill=tk.Y, side=tk.LEFT)
    progressBar.pack(fill=tk.Y, side=tk.LEFT)
    lbl_rate.pack(fill=tk.Y, side=tk.LEFT)
    frm_progress.pack()

    def upload():

        path = fd.askopenfilename()
        if len(path) < 2: return

        path = os.path.normpath(path)
        *directory, filename = path.split(os.sep)
        directory = os.sep.join(directory)
        *filename, filetype = filename.split('.')
        filename = '.'.join(filename)
        lbl_progress['text'] = "Uploading " + filename+"."+filetype
        window.update_idletasks()
        connection.sendFile(directory, filename, filetype, log = progress)

    btn = tk.Button(
        text='Upload',
        command=upload,
        master=frm_progress
    )
    btn.pack(padx=5, pady=5)

    def on_close():
        # if connection udp
        connection.close()
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", on_close )
    window.mainloop()





connectionPrompt()


