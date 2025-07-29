import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import zipfile
import rarfile

# Add the parent directory to the path so we can import push_to_kindle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from komga_custom import push_to_kindle

class TestPushToKindle(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for test files."""
        self.test_dir = tempfile.mkdtemp()
        self.test_library_path = '/mnt/dockerHDD/opt/myApp/komga_dev/komga/test_library'
        os.makedirs(self.test_library_path, exist_ok=True)

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.test_dir)
        if os.path.exists(self.test_library_path):
            shutil.rmtree(self.test_library_path)

    def create_dummy_cbr(self, filename="test.cbr"):
        """Creates a dummy CBR file."""
        cbr_path = os.path.join(self.test_library_path, filename)
        with open(cbr_path, "w") as f:
            f.write("this is a test cbr file")
        return cbr_path

    def test_convert_cbr_to_cbz(self):
        """Test the CBR to CBZ conversion."""
        cbr_path = self.create_dummy_cbr()

        # To make a valid rar file for testing, we can't just write text.
        # We will mock rarfile.RarFile
        with patch('rarfile.RarFile') as mock_rarfile:
            mock_rar_instance = MagicMock()
            
            # Create a mock RarInfo object
            mock_rar_info = MagicMock()
            mock_rar_info.filename = 'test.jpg'
            mock_rar_info.is_file.return_value = True
            
            mock_rar_instance.infolist.return_value = [mock_rar_info]
            mock_rar_instance.read.return_value = b'imagedata'
            mock_rarfile.return_value.__enter__.return_value = mock_rar_instance

            cbz_path = push_to_kindle.convert_cbr_to_cbz(cbr_path, self.test_dir)
            self.assertTrue(cbz_path.endswith('.cbz'))
            self.assertTrue(os.path.exists(cbz_path))

            with zipfile.ZipFile(cbz_path, 'r') as zf:
                self.assertEqual(len(zf.infolist()), 1)
                self.assertEqual(zf.infolist()[0].filename, 'test.jpg')

if __name__ == '__main__':
    unittest.main()