from matplotlib import pyplot as plt
from matplotlib import cm
import tkinter as tk
from tkinter import filedialog as fdialog
import spe_loader as sl


class SpeTool:
    def __init__(self, spe_file):
        self.file = spe_file

    def image(self, frame=0, roi=0):
        """
        Images loaded data for a specific frame and region of interest.
        """
        img = plt.imshow(self.file.data[frame][roi], cmap=cm.get_cmap('hot'))
        plt.title(self.file.filepath)
        return img

    def specplot(self, frame=0, roi=0):
        """
        Plots loaded data for a specific frame, assuming the data is a one dimensional spectrum.
        """
        spectrum = plt.plot(self.file.wavelength.transpose(), self.file.data[frame][roi].transpose())
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

    @property
    def data(self):
        print('Deprecation Warning: if using SpeTools from spe2py, use object.file.data instead.')
        return self.file.data

    @property
    def footer(self):
        print('Deprecation Warning: if using SpeTools from spe2py, use object.file.footer instead.')
        return self.file.footer

    @property
    def wavelength(self):
        print('Deprecation Warning: if using SpeTools from spe2py, use object.file.wavelength instead.')
        return self.file.wavelength


def imgobject(spe_file, frame=0, roi=0):
    """
    Unbound function for imaging loaded data
    """
    img = plt.imshow(getattr(spe_file, 'data')[frame][roi], cmap=cm.get_cmap('hot'))
    return img


def load():
    file_paths = get_files(True)
    batch = sl.load_from_files(file_paths)
    print('File(s) have been loaded into SpeTool objects')
    if isinstance(batch, list):
        return [SpeTool(file) for file in batch]
    else:
        return SpeTool(batch)


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
            plt.figure()
            obj[i].image()
    else:
        plt.figure()
        obj.image()
    plt.show()
