import wx
from app.core.config import CONFIG

class LoginDialog(wx.Dialog):
    def __init__(self, default_username : str, callback_on_complete, test_af_creds):
        super().__init__(None, title=CONFIG.APP_NAME, size=(300, 200))
        icon = wx.Icon("Assets/LBS_AF_Logo.ico", wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)
        
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Username
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        user_label = wx.StaticText(panel, label="Username:")
        self.user_text = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.user_text.SetValue(default_username)
        hbox1.Add(user_label, 0, wx.ALL, 5)
        hbox1.Add(self.user_text, 1, wx.ALL, 5)
        vbox.Add(hbox1, 0, wx.EXPAND)
        
        # Password
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        pass_label = wx.StaticText(panel, label="Password:")
        self.pass_text = wx.TextCtrl(panel, style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)
        hbox2.Add(pass_label, 0, wx.ALL, 5)
        hbox2.Add(self.pass_text, 1, wx.ALL, 5)
        vbox.Add(hbox2, 0, wx.EXPAND)
        
        # Remember Me Checkbox
        self.remember_checkbox = wx.CheckBox(panel, label="Remember Me")
        self.remember_checkbox.SetValue(False)
        vbox.Add(self.remember_checkbox, 0, wx.LEFT | wx.TOP, 10)
        
        # Buttons
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        login_btn = wx.Button(panel, label="Login")
        cancel_btn = wx.Button(panel, label="Cancel")
        hbox3.Add(login_btn, 0, wx.ALL, 5)
        hbox3.Add(cancel_btn, 0, wx.ALL, 5)
        vbox.Add(hbox3, 0, wx.ALIGN_CENTER)
        
        # Events
        login_btn.Bind(wx.EVT_BUTTON, self.on_login)
        cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.user_text.Bind(wx.EVT_TEXT_ENTER, self.on_username_enter)
        self.pass_text.Bind(wx.EVT_TEXT_ENTER, self.on_login)
        self.Bind(wx.EVT_CLOSE, self.on_cancel)  # Handle window 'X' button

        panel.SetSizer(vbox)
        self.Centre()  # Center the dialog
        self.pass_text.SetFocus()  # Focus starts on the password field

        # Store callbacks for when the window is complete.
        self.callback_on_complete = callback_on_complete
        self.test_af_creds = test_af_creds

    def on_username_enter(self, event):
        self.pass_text.SetFocus()

    def on_login(self, event):
        username = self.user_text.GetValue()
        password = self.pass_text.GetValue()
        conn = self.test_af_creds(username, password)
        if conn:
            remember_me = self.remember_checkbox.GetValue()
            # Close up
            self.callback_on_complete(
                username,
                password,
                remember_me,
                conn
            )
            self.Destroy()
        else:
            wx.MessageBox("Invalid username or password", "Error", wx.OK | wx.ICON_ERROR)
    
    def on_cancel(self, event):
        self.Destroy()
        wx.GetApp().ExitMainLoop()
