"""
@package wxgui

@brief Main Python application for GRASS wxPython GUI

Classes:
 - wxgui::GMApp

(C) 2006-2015 by the GRASS Development Team

This program is free software under the GNU General Public License
(>=v2). Read the file COPYING that comes with GRASS for details.

@author Michael Barton (Arizona State University)
@author Jachym Cepicky (Mendel University of Agriculture)
@author Martin Landa <landa.martin gmail.com>
@author Vaclav Petras <wenzeslaus gmail.com> (menu customization)
"""

import os
import sys
import json
import getopt

# i18n is taken care of in the grass library code.
# So we need to import it before any of the GUI code.
from grass.exceptions import Usage
from grass.script.core import set_raise_on_error, warning, error

from core import globalvar
from core.utils import registerPid, unregisterPid
from core.settings import UserSettings

import wx
import threading

import logging
from flask import Flask, request
from werkzeug.serving import make_server

flask_log = logging.getLogger("werkzeug")
flask_log.setLevel(logging.ERROR)

flask = Flask(__name__)
frame = None

# import adv and html before wx.App is created, otherwise
# we get annoying "Debug: Adding duplicate image handler for 'Windows bitmap file'"
# during start up, remove when not needed
import wx.adv
import wx.html

FLASK_TIMEOUT = 10
JSON_WRAPPER = lambda value: { "code": value }

try:
    import wx.lib.agw.advancedsplash as SC
except ImportError:
    SC = None


def prejsonify(obj: any):
    return json.loads(json.dumps(
        obj.__dict__ if hasattr(obj, "__dict__") else obj,
        default=lambda _: "N/A"
    ))

@flask.route("/version", methods=["GET"])
def get_version():
    return "1.0"

@flask.route("/init/cmd", methods=["GET"])
def init_cmd():
    global frame
    assert frame is not None

    from main_window.frame import response_event
    response_event.clear()
    wx.CallAfter(frame.InitDisableCmd)

    if response_event.wait(timeout=FLASK_TIMEOUT):
        from main_window.frame import response_value
        if response_value:
            return "OK"
    return "ERROR"

@flask.route("/init/map", methods=["POST"])
def init_map():
    global frame
    assert frame is not None

    from main_window.frame import response_event
    response_event.clear()

    params = request.get_json()
    wx.CallAfter(
        frame.InitMapset,
        grassdb=params["grassdb"],
        location=params["location"],
        mapset=params["mapset"]
    )

    if response_event.wait(timeout=FLASK_TIMEOUT):
        from main_window.frame import response_value
        if response_value:
            return "OK"
    return "ERROR"

@flask.route("/init/layer", methods=["POST"])
def init_layer():
    global frame
    assert frame is not None

    from main_window.frame import response_event
    response_event.clear()

    params = request.get_json()
    wx.CallAfter(
        frame.DisplayLayer,
        query=params["query"]
    )

    if response_event.wait(timeout=FLASK_TIMEOUT):
        from main_window.frame import response_value
        if response_value:
            return "OK"
    return "ERROR"

@flask.route("/init/scale", methods=["POST"])
def init_scale():
    global frame
    assert frame is not None

    from main_window.frame import response_event
    response_event.clear()

    params = request.get_json()
    wx.CallAfter(
        frame.InitMapScale,
        scale=params["scale"]
    )

    if response_event.wait(timeout=FLASK_TIMEOUT):
        from main_window.frame import response_value
        if response_value:
            return "OK"
    return "ERROR"

@flask.route("/dump", methods=["GET"])
def status_dump():
    global frame
    assert frame is not None

    return {
        "layers": [prejsonify(item) for item in frame.pg_panel.maptree.Map.layers],
        "windows": [{
            "name": item._data[0]["maplayer"].name,
            **prejsonify(item)
        } for item in frame.pg_panel.maptree._itemWithWindow],
        "toolbars": {
            "keys": list(frame.mainnotebook._tabs._pages[0].window.toolbars.keys()),
            "shown": frame.mainnotebook._tabs._pages[0].window.toolbars["map"].IsShown(),
            "layer": prejsonify(frame.mainnotebook._tabs._pages[0].window.toolbars["vdigit"].mapLayer) \
                if "vdigit" in frame.mainnotebook._tabs._pages[0].window.toolbars else None
        },
        "statusbar": {
            "mode": frame.mainnotebook._tabs._pages[0].window.statusbarManager._mode,
            "scale": frame.mainnotebook._tabs._pages[0].window.GetMapScale()
        },
        "region": frame.mainnotebook._tabs._pages[0].window.Map.region,
        "output": frame.goutput.cmdOutput.GetText()
    }

@flask.route("/gcmd", methods=["POST"])
def gcmd():
    global frame
    assert frame is not None

    from main_window.frame import response_event
    response_event.clear()

    params = request.get_json()
    wx.CallAfter(frame.GCommand, params["cmd"], **params["kwargs"])

    if response_event.wait(timeout=FLASK_TIMEOUT):
        from main_window.frame import response_value
        print(response_value[2])
        return {
            "returncode": response_value[0],
            "stdout": json.loads(response_value[1]) \
                if "format" in params["kwargs"] \
                    and params["kwargs"]["format"] == "json" \
                else response_value[1]
        }
    return "ERROR"

@flask.route("/quit", methods=["POST"])
def quit():
    global frame
    assert frame is not None
    wx.CallAfter(frame._quitGRASS)

class GMApp(wx.App):
    def __init__(self, workspace=None):
        """Main GUI class.

        :param workspace: path to the workspace file
        """
        self.workspaceFile = workspace

        # call parent class initializer
        wx.App.__init__(self, False)

        self.locale = wx.Locale(language=wx.LANGUAGE_DEFAULT)

    def OnInit(self):
        """Initialize all available image handlers

        :return: True
        """
        # Internal and display name of the app (if supported by/on platform)
        self.SetAppName("GRASS GIS")
        self.SetVendorName("The GRASS Development Team")

        # create splash screen
        introImagePath = os.path.join(globalvar.IMGDIR, "splash_screen.png")
        introImage = wx.Image(introImagePath, wx.BITMAP_TYPE_PNG)
        introBmp = introImage.ConvertToBitmap()
        wx.adv.SplashScreen(
            bitmap=introBmp,
            splashStyle=wx.adv.SPLASH_CENTRE_ON_SCREEN | wx.adv.SPLASH_TIMEOUT,
            milliseconds=3000,
            parent=None,
            id=wx.ID_ANY,
        )

        wx.GetApp().Yield()

        def show_main_gui():
            # create and show main frame
            single = UserSettings.Get(
                group="appearance", key="singleWindow", subkey="enabled"
            )
            if single:
                from main_window.frame import GMFrame
            else:
                from lmgr.frame import GMFrame
            try:
                global frame
                frame = GMFrame(
                    parent=None, id=wx.ID_ANY, workspace=self.workspaceFile
                )
            except Exception as err:
                min_required_wx_version = [4, 2, 0]
                if not globalvar.CheckWxVersion(min_required_wx_version):
                    error(err)
                    warning(
                        _(
                            "Current version of wxPython {} is lower than "
                            "minimum required version {}".format(
                                wx.__version__,
                                ".".join(map(str, min_required_wx_version)),
                            )
                        )
                    )
                else:
                    raise
            else:
                frame.Maximize(True)
                frame.Show()
                self.SetTopWindow(frame)

        wx.CallAfter(show_main_gui)

        return True

    def OnExit(self):
        """Clean up on exit"""
        unregisterPid(os.getpid())
        return super().OnExit()


def printHelp():
    """Print program help"""
    print("Usage:", file=sys.stderr)
    print(" python wxgui.py [options]", file=sys.stderr)
    print("%sOptions:" % os.linesep, file=sys.stderr)
    print(" -w\t--workspace file\tWorkspace file to load", file=sys.stderr)
    sys.exit(1)


def process_opt(opts, args):
    """Process command-line arguments"""
    workspaceFile = None
    for o, a in opts:
        if o in ("-h", "--help"):
            printHelp()

        elif o in ("-w", "--workspace"):
            if a != "":
                workspaceFile = str(a)
            else:
                workspaceFile = args.pop(0)

    return workspaceFile

class FlaskThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        flask_port = os.environ.get("FLASK_PORT", 8000)
        self.server = make_server("0.0.0.0", flask_port, flask)
        self.ctx = flask.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hw:", ["help", "workspace"])
        except getopt.error as msg:
            raise Usage(msg)
    except Usage as err:
        print(err.msg, file=sys.stderr)
        print(sys.stderr, "for help use --help", file=sys.stderr)
        printHelp()

    workspaceFile = process_opt(opts, args)
    app = GMApp(workspaceFile)

    # suppress wxPython logs
    q = wx.LogNull()
    set_raise_on_error(True)

    # register GUI PID
    registerPid(os.getpid())

    flask_thread = FlaskThread()
    flask_thread.start()
    app.MainLoop()


if __name__ == "__main__":
    sys.exit(main())
