import gbulb
from os import path
import sys

top_level = path.abspath(path.join(path.dirname(__file__), '..'))
sys.path.append(top_level)
gbulb.install()