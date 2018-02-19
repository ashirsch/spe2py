from matplotlib import pyplot as plt
from matplotlib import cm
import tkinter as tk
from tkinter import filedialog as fdialog
import spe_loader as sl


class SpeTool:
    def __init__(self, spe_file):
        self.spe_file = spe_file

    def image(self, frame=0, roi=0):
        """
        Images loaded data for a specific frame and region of interest.
        """
        img = plt.imshow(self.spe_file.data[frame][roi], cmap=cm.get_cmap('hot'))
        plt.title(self.spe_file.filepath)
        return img

    def specplot(self, frame=0, roi=0):
        """
        Plots loaded data for a specific frame, assuming the data is a one dimensional spectrum.
        """
        spectrum = plt.plot(self.spe_file.wavelength.transpose(), self.spe_file.data[frame][roi].transpose())
        plt.grid()
        return spectrum

    def xmltree(self, footer, ind=-1):
        """
        Prints the untangle footer object in tree form to easily view metadata fields. Ignores object elements that
        contain lists (e.g. ..Spectrometer.Turrets.Turret).
        """
        if dir(footer):
            ind += 1
            for item in dir(footer):
                if isinstance(getattr(footer, item), list):
                    continue
                else:
                    print(ind * ' -->', item)
                    self.xmltree(getattr(footer, item), ind)


def imgobject(spe_file, frame=0, roi=0):
    """
    Unbound function for imaging loaded data
    """
    img = plt.imshow(getattr(spe_file, 'data')[frame][roi], cmap=cm.get_cmap('hot'))
    return img


def load():
    file_paths = get_files(True)
    batch = sl.load_from_files(file_paths)
    return batch


def get_files(mult=False):
    """
    Uses tkinter to allow UI source file selection
    Adapted from: http://stackoverflow.com/a/7090747
    """
    root = tk.Tk()
    root.withdraw()
    filepaths = fdialog.askopenfilenames()
    if not mult:
        filepaths = filepaths[0]
    root.destroy()
    return filepaths


if __name__ == "__main__":
    obj = load()
    if isinstance(obj, list):
        for i in range(len(obj)):
            spe_tool = SpeTool(obj[i])
            plt.figure()
            spe_tool.image()
    else:
        spe_tool = SpeTool(obj)
        plt.figure()
        spe_tool.image()
    plt.show()
