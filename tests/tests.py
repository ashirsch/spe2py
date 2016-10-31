#!/usr/bin/env python
import os
import unittest
import spe2py as spe


class BasicFileLoading(unittest.TestCase):
    """ Loading different files individually """
    def test_load_full_sensor(self):
        obj = spe.SpeFile(os.path.join(os.path.dirname(__file__), "test_files/full_sensor_image.spe"))
        self.assert_(obj is not None)
        self.assert_(obj.data is not None)
        self.assert_(obj.data[0][0].shape == (1024, 1024))
        self.assert_(obj.nframes == 1)
        self.assert_(obj.nroi == 1)

    def test_load_small_roi(self):
        obj = spe.SpeFile(os.path.join(os.path.dirname(__file__), "test_files/small_roi.spe"))
        self.assert_(obj is not None)
        self.assert_(obj.data is not None)
        self.assert_(obj.data[0][0].shape == (638, 705))
        self.assertEqual(obj.nframes, 1)
        self.assertEqual(obj.nroi, 1)

    def test_load_mult_roi(self):
        obj = spe.SpeFile(os.path.join(os.path.dirname(__file__),
                                       "test_files/two_rectangular_rois_different_binning.spe"))
        self.assert_(obj is not None)
        self.assert_(obj.data is not None)
        self.assert_(obj.data[0][0].shape == (638, 705))
        self.assert_(obj.data[0][1].shape == (55, 80))
        self.assertEqual(obj.roi[0]['xBinning'], '1')
        self.assertEqual(obj.roi[1]['xBinning'], '4')
        self.assertEqual(obj.roi[1]['yBinning'], '2')

    def test_load_one_dim(self):
        obj = spe.SpeFile(os.path.join(os.path.dirname(__file__), "test_files/one_dimensional_spectrum.spe"))
        self.assert_(obj is not None)
        self.assert_(obj.data is not None)
        self.assert_(obj.data[0][0].shape == (1, 1024))

    def test_load_complex_file(self):
        obj = spe.SpeFile(os.path.join(os.path.dirname(__file__),
                                       "test_files/ten_frames_two_rois_different_binning.spe"))
        self.assert_(obj is not None)
        self.assert_(obj.data is not None)
        self.assert_(obj.data[0][0].shape == (177, 626))
        self.assert_(obj.data[0][1].shape == (46, 256))
        self.assertEqual(obj.nframes, 10)
        self.assertEqual(obj.nroi, 2)

    def test_load_step_and_glue(self):
        obj = spe.SpeFile(os.path.join(os.path.dirname(__file__), "test_files/step_and_glue.spe"))
        self.assert_(obj is not None)
        self.assert_(obj.data is not None)
        self.assert_(obj.data[0][0].shape == (1567, 1024))
        self.assert_(obj.nframes == 1)
        self.assert_(obj.nroi == 1)


class ImagingFunctionality(unittest.TestCase):
    """Test two imaging methods (specplot and image)"""
    def test_default_image_method(self):
        obj = spe.SpeFile(os.path.join(os.path.dirname(__file__), "test_files/full_sensor_image.spe"))
        img = obj.image()
        self.assert_(img is not None)

    def test_image_method_with_args(self):
        obj = spe.SpeFile(os.path.join(os.path.dirname(__file__),
                                       "test_files/ten_frames_two_rois_different_binning.spe"))
        img1 = obj.image(1, 0)
        img2 = obj.image(2, 0)
        self.assert_(img1 is not None and img2 is not None)
        self.assertNotEqual(img1, img2)
        img3 = obj.image(1, 1)
        self.assertNotEqual(img1, img3)

    def test_spectrum_method(self):
        obj = spe.SpeFile(os.path.join(os.path.dirname(__file__), "test_files/one_dimensional_spectrum.spe"))
        spec = obj.specplot()
        self.assert_(spec is not None)


if __name__ == '__main__':
    unittest.main()
