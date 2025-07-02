import wx
import wx.grid as gridlib

# The table window with 4 columns and dummy data
class TableFrame(wx.Frame):
    def __init__(self, parent=None, title="Table Window"):
        super(TableFrame, self).__init__(parent, title=title, size=(500, 300))

        panel = wx.Panel(self)
        grid = gridlib.Grid(panel)
        grid.CreateGrid(5, 4)  # 5 rows, 4 columns

        # Set column labels
        col_labels = ['Name', 'Age', 'Country', 'Occupation']
        for i, label in enumerate(col_labels):
            grid.SetColLabelValue(i, label)

        # Add some dummy data
        dummy_data = [
            ['Alice', '30', 'USA', 'Engineer'],
            ['Bob', '25', 'Canada', 'Designer'],
            ['Charlie', '35', 'UK', 'Teacher'],
            ['Diana', '28', 'Australia', 'Developer'],
            ['Eve', '40', 'Germany', 'Manager']
        ]

        for row_idx, row in enumerate(dummy_data):
            for col_idx, value in enumerate(row):
                grid.SetCellValue(row_idx, col_idx, value)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)


# Main application window
class MainFrame(wx.Frame):
    def __init__(self):
        super(MainFrame, self).__init__(None, title="Main Window", size=(300, 200))

        panel = wx.Panel(self)
        btn = wx.Button(panel, label="Open Table Window")
        btn.Bind(wx.EVT_BUTTON, self.on_open_table)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(btn, 0, wx.CENTER | wx.ALL, 20)
        panel.SetSizer(sizer)

    def on_open_table(self, event):
        table_frame = TableFrame(self)
        table_frame.Show()

# Run the application
if __name__ == "__main__":
    app = wx.App(False)
    frame = MainFrame()
    frame.Show()
    app.MainLoop()
