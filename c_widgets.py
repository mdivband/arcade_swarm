from matplotlib.patches import Rectangle

class Annotate(object):
    def __init__(self, ax, areas, rects):
        self.ax = ax
        self.areas = areas
        self.rects = rects
        self.rect = Rectangle((0,0), 0, 0, color='orange', alpha=0.5)
        self.x0 = None
        self.y0 = None
        self.x1 = None
        self.y1 = None
        self.ax.add_patch(self.rect)
        self.ax.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.ax.figure.canvas.mpl_connect('button_release_event', self.on_release)

    def on_press(self, event):
        if event.inaxes == self.ax:
            self.x0 = event.xdata
            self.y0 = event.ydata

    def on_release(self, event):
        if event.inaxes == self.ax:
            self.x1 = event.xdata
            self.y1 = event.ydata
            if event.button == 1:
                self.areas.append([self.x0, self.y0, 
                                self.x1, self.y1, "appended", "a"])
            elif event.button == 3:
                self.areas.append([self.x0, self.y0, 
                                self.x1, self.y1, "appended", "d"])
            self.rect.set_width(self.x1 - self.x0)
            self.rect.set_height(self.y1 - self.y0)
            self.rect.set_xy((self.x0, self.y0))
            self.rect.set_visible(False)
        