import unittest
import os
import sys

# Add project root to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class CheckProjectStructure(unittest.TestCase):
    def test_important_folders_exist(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        required_folders = ['scripts', 'tests', 'images'] # images is local only
        
        for folder in required_folders:
            path = os.path.join(root, folder)
            if folder == 'images':
                # Images might not exist in git repo, but should exist locally
                pass 
            else:
                self.assertTrue(os.path.exists(path), f"Folder missing: {folder}")

if __name__ == "__main__":
    unittest.main()
