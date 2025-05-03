import re
import csv
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import os

# Define the input string as a constant
DATA_STRING_SQUARE = """
  - Network_Rack_50 (ID: 11): X=0, Y=0 (W=40, H=40)
  - Transformer_1000 (ID: 2): X=40, Y=0 (W=100, H=100)
  - Network_Rack_50 (ID: 11): X=140, Y=0 (W=40, H=40)
  - Network_Rack_50 (ID: 11): X=180, Y=0 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=220, Y=0 (W=40, H=40)
  - Network_Rack_50 (ID: 11): X=260, Y=0 (W=40, H=40)
  - Water_Treatment_50 (ID: 6): X=300, Y=0 (W=50, H=50)
  - Water_Treatment_50 (ID: 6): X=350, Y=0 (W=50, H=50)
  - Server_Rack_200 (ID: 15): X=400, Y=0 (W=40, H=40)
  - Server_Rack_100 (ID: 14): X=440, Y=0 (W=40, H=40)
  - Network_Rack_100 (ID: 12): X=480, Y=0 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=520, Y=0 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=560, Y=0 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=600, Y=0 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=640, Y=0 (W=40, H=40)
  - Data_Rack_500 (ID: 19): X=680, Y=0 (W=40, H=40)
  - Data_Rack_250 (ID: 18): X=720, Y=0 (W=40, H=40)
  - Data_Rack_250 (ID: 18): X=0, Y=40 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=140, Y=40 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=400, Y=40 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=440, Y=40 (W=40, H=40)
  - Water_Supply_100 (ID: 4): X=0, Y=100 (W=50, H=50)
  - Water_Chiller_100 (ID: 9): X=50, Y=100 (W=100, H=100)
  - Water_Chiller_400 (ID: 10): X=150, Y=100 (W=300, H=100)
  - Network_Rack_50 (ID: 11): X=0, Y=200 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=40, Y=200 (W=40, H=40)
  - Transformer_1000 (ID: 2): X=80, Y=200 (W=100, H=100)
  - Server_Rack_200 (ID: 15): X=180, Y=200 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=220, Y=200 (W=40, H=40)
  - Transformer_5000 (ID: 3): X=260, Y=200 (W=200, H=200)
  - Server_Rack_200 (ID: 15): X=0, Y=240 (W=40, H=40)
  - Network_Rack_50 (ID: 11): X=40, Y=240 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=180, Y=240 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=220, Y=240 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=0, Y=280 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=180, Y=280 (W=40, H=40)
  - Water_Chiller_100 (ID: 9): X=40, Y=300 (W=100, H=100)
  - Network_Rack_100 (ID: 12): X=0, Y=320 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=0, Y=360 (W=40, H=40)
  - Water_Chiller_100 (ID: 9): X=0, Y=400 (W=100, H=100)
  - Server_Rack_200 (ID: 15): X=100, Y=400 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=140, Y=400 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=180, Y=400 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=220, Y=400 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=100, Y=440 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=140, Y=440 (W=40, H=40)
  """

DATA_STRING_SUPERCOMPUTER = """
  - Transformer_100 (ID: 1): X=0, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=80, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=120, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=160, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=200, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=240, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=280, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=320, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=360, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=440, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=480, Y=0 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=521, Y=0 (W=50, H=50)
  - Transformer_100 (ID: 1): X=571, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=611, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=651, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=691, Y=0 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=740, Y=0 (W=50, H=50)
  - Transformer_100 (ID: 1): X=790, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=830, Y=0 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=880, Y=0 (W=50, H=50)
  - Transformer_100 (ID: 1): X=940, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=980, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1020, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1060, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1100, Y=0 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1140, Y=0 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1190, Y=0 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1240, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1290, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1330, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1370, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1410, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1450, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1490, Y=0 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1530, Y=0 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1580, Y=0 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1640, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1680, Y=0 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1720, Y=0 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1760, Y=0 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1830, Y=0 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1880, Y=0 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1930, Y=0 (W=50, H=50)
  - Transformer_100 (ID: 1): X=0, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=80, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=120, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=160, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=200, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=240, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=360, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=580, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=620, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=660, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=700, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=840, Y=45 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=990, Y=45 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1290, Y=45 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1340, Y=45 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1390, Y=45 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1450, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1640, Y=45 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1690, Y=45 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=281, Y=46 (W=50, H=50)
  - Transformer_100 (ID: 1): X=400, Y=47 (W=40, H=45)
  - Transformer_1000 (ID: 2): X=440, Y=50 (W=100, H=100)
  - Water_Supply_100 (ID: 4): X=740, Y=50 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=790, Y=50 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=891, Y=50 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1040, Y=50 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1090, Y=50 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1140, Y=50 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1190, Y=50 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1240, Y=50 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1490, Y=50 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1540, Y=50 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1590, Y=50 (W=50, H=50)
  - Transformer_1000 (ID: 2): X=1730, Y=50 (W=100, H=100)
  - Water_Supply_500 (ID: 5): X=1840, Y=50 (W=150, H=100)
  - Transformer_100 (ID: 1): X=0, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=80, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=120, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=160, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=200, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=240, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=331, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=540, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=580, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=620, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=660, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=700, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1680, Y=90 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=92 (W=40, H=45)
  - Transformer_100 (ID: 1): X=990, Y=95 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1330, Y=95 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1390, Y=95 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=740, Y=100 (W=50, H=50)
  - Transformer_100 (ID: 1): X=790, Y=100 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=890, Y=100 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=940, Y=100 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1040, Y=100 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1100, Y=100 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1140, Y=100 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1240, Y=100 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1490, Y=100 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1540, Y=100 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1600, Y=100 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=80, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=120, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=160, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=200, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=240, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=280, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=320, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=360, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=570, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=620, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=660, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=700, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=830, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1680, Y=135 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=137 (W=40, H=45)
  - Transformer_100 (ID: 1): X=990, Y=140 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1330, Y=140 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1370, Y=145 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1490, Y=145 (W=40, H=45)
  - Transformer_100 (ID: 1): X=440, Y=150 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=480, Y=150 (W=50, H=50)
  - Transformer_100 (ID: 1): X=530, Y=150 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=740, Y=150 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=890, Y=150 (W=50, H=50)
  - Transformer_100 (ID: 1): X=940, Y=150 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1040, Y=150 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1240, Y=150 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1530, Y=150 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1570, Y=150 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1730, Y=150 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1770, Y=150 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1880, Y=150 (W=50, H=50)
  - Transformer_100 (ID: 1): X=0, Y=180 (W=40, H=45)
  - Transformer_100 (ID: 1): X=73, Y=180 (W=40, H=45)
  - Transformer_100 (ID: 1): X=113, Y=180 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=153, Y=180 (W=50, H=50)
  - Transformer_100 (ID: 1): X=203, Y=180 (W=40, H=45)
  - Transformer_100 (ID: 1): X=281, Y=180 (W=40, H=45)
  - Transformer_100 (ID: 1): X=360, Y=180 (W=40, H=45)
  - Transformer_100 (ID: 1): X=580, Y=180 (W=40, H=45)
  - Transformer_100 (ID: 1): X=620, Y=180 (W=40, H=45)
  - Transformer_100 (ID: 1): X=660, Y=180 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1680, Y=180 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=182 (W=40, H=45)
  - Transformer_100 (ID: 1): X=980, Y=185 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1490, Y=190 (W=40, H=45)
  - Transformer_100 (ID: 1): X=440, Y=195 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=530, Y=195 (W=50, H=50)
  - Transformer_100 (ID: 1): X=940, Y=195 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1530, Y=195 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1720, Y=195 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=480, Y=200 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=890, Y=200 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=1040, Y=200 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1240, Y=200 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1280, Y=200 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=1880, Y=200 (W=50, H=50)
  - Transformer_100 (ID: 1): X=0, Y=225 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=225 (W=40, H=45)
  - Transformer_100 (ID: 1): X=80, Y=225 (W=40, H=45)
  - Transformer_100 (ID: 1): X=203, Y=225 (W=40, H=45)
  - Transformer_100 (ID: 1): X=281, Y=225 (W=40, H=45)
  - Transformer_100 (ID: 1): X=321, Y=225 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1680, Y=225 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=227 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1530, Y=240 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1720, Y=240 (W=40, H=45)
  - Transformer_100 (ID: 1): X=571, Y=245 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=480, Y=250 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1041, Y=250 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=270 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=40, Y=270 (W=50, H=50)
  - Water_Supply_500 (ID: 5): X=90, Y=270 (W=150, H=100)
  - Transformer_100 (ID: 1): X=240, Y=270 (W=40, H=45)
  - Transformer_100 (ID: 1): X=280, Y=270 (W=40, H=45)
  - Transformer_100 (ID: 1): X=320, Y=270 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=272 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1720, Y=285 (W=40, H=45)
  - Transformer_100 (ID: 1): X=571, Y=290 (W=40, H=45)
  - Transformer_100 (ID: 1): X=1020, Y=295 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=315 (W=40, H=45)
  - Transformer_100 (ID: 1): X=241, Y=315 (W=40, H=45)
  - Transformer_100 (ID: 1): X=281, Y=315 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=40, Y=320 (W=50, H=50)
  - Transformer_100 (ID: 1): X=1720, Y=330 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=360 (W=40, H=45)
  - Transformer_100 (ID: 1): X=240, Y=360 (W=40, H=45)
  - Transformer_100 (ID: 1): X=280, Y=360 (W=40, H=45)
  - Transformer_100 (ID: 1): X=320, Y=360 (W=40, H=45)
  - Transformer_100 (ID: 1): X=360, Y=360 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=360 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=40, Y=370 (W=50, H=50)
  - Transformer_100 (ID: 1): X=0, Y=405 (W=40, H=45)
  - Transformer_100 (ID: 1): X=90, Y=405 (W=40, H=45)
  - Transformer_100 (ID: 1): X=130, Y=405 (W=40, H=45)
  - Transformer_100 (ID: 1): X=170, Y=405 (W=40, H=45)
  - Transformer_100 (ID: 1): X=210, Y=405 (W=40, H=45)
  - Transformer_100 (ID: 1): X=250, Y=405 (W=40, H=45)
  - Transformer_100 (ID: 1): X=290, Y=405 (W=40, H=45)
  - Transformer_100 (ID: 1): X=41, Y=420 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=450 (W=40, H=45)
  - Transformer_100 (ID: 1): X=280, Y=450 (W=40, H=45)
  - Transformer_100 (ID: 1): X=320, Y=450 (W=40, H=45)
  - Transformer_100 (ID: 1): X=360, Y=450 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=450 (W=40, H=45)
  - Transformer_5000 (ID: 3): X=80, Y=465 (W=200, H=200)
  - Transformer_100 (ID: 1): X=0, Y=495 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=495 (W=40, H=45)
  - Transformer_100 (ID: 1): X=280, Y=495 (W=40, H=45)
  - Transformer_100 (ID: 1): X=320, Y=495 (W=40, H=45)
  - Transformer_100 (ID: 1): X=360, Y=495 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=495 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=540 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=540 (W=40, H=45)
  - Transformer_100 (ID: 1): X=280, Y=540 (W=40, H=45)
  - Transformer_100 (ID: 1): X=320, Y=540 (W=40, H=45)
  - Transformer_100 (ID: 1): X=360, Y=540 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=540 (W=40, H=45)
  - Transformer_100 (ID: 1): X=440, Y=540 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=585 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=585 (W=40, H=45)
  - Transformer_100 (ID: 1): X=280, Y=585 (W=40, H=45)
  - Transformer_100 (ID: 1): X=320, Y=585 (W=40, H=45)
  - Transformer_100 (ID: 1): X=360, Y=585 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=585 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=630 (W=40, H=45)
  - Transformer_100 (ID: 1): X=280, Y=630 (W=40, H=45)
  - Transformer_100 (ID: 1): X=420, Y=630 (W=40, H=45)
  - Transformer_100 (ID: 1): X=460, Y=630 (W=40, H=45)
  - Transformer_100 (ID: 1): X=500, Y=630 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=40, Y=665 (W=50, H=50)
  - Transformer_100 (ID: 1): X=160, Y=665 (W=40, H=45)
  - Transformer_100 (ID: 1): X=200, Y=665 (W=40, H=45)
  - Transformer_1000 (ID: 2): X=320, Y=665 (W=100, H=100)
  - Transformer_100 (ID: 1): X=0, Y=675 (W=40, H=45)
  - Transformer_100 (ID: 1): X=90, Y=675 (W=40, H=45)
  - Transformer_100 (ID: 1): X=240, Y=675 (W=40, H=45)
  - Transformer_100 (ID: 1): X=200, Y=710 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=715 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=720 (W=40, H=45)
  - Transformer_100 (ID: 1): X=80, Y=720 (W=40, H=45)
  - Transformer_100 (ID: 1): X=120, Y=720 (W=40, H=45)
  - Transformer_100 (ID: 1): X=160, Y=720 (W=40, H=45)
  - Transformer_100 (ID: 1): X=240, Y=720 (W=40, H=45)
  - Transformer_100 (ID: 1): X=280, Y=720 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=765 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=765 (W=40, H=45)
  - Transformer_100 (ID: 1): X=80, Y=765 (W=40, H=45)
  - Transformer_100 (ID: 1): X=120, Y=765 (W=40, H=45)
  - Water_Supply_500 (ID: 5): X=170, Y=765 (W=150, H=100)
  - Transformer_100 (ID: 1): X=320, Y=765 (W=40, H=45)
  - Transformer_100 (ID: 1): X=360, Y=765 (W=40, H=45)
  - Transformer_100 (ID: 1): X=400, Y=765 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=810 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=40, Y=810 (W=50, H=50)
  - Transformer_100 (ID: 1): X=90, Y=810 (W=40, H=45)
  - Transformer_100 (ID: 1): X=130, Y=810 (W=40, H=45)
  - Transformer_100 (ID: 1): X=320, Y=810 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=855 (W=40, H=45)
  - Transformer_100 (ID: 1): X=90, Y=855 (W=40, H=45)
  - Transformer_100 (ID: 1): X=320, Y=855 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=860 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=160, Y=865 (W=50, H=50)
  - Transformer_100 (ID: 1): X=0, Y=900 (W=40, H=45)
  - Transformer_100 (ID: 1): X=80, Y=900 (W=40, H=45)
  - Transformer_100 (ID: 1): X=120, Y=900 (W=40, H=45)
  - Transformer_100 (ID: 1): X=40, Y=905 (W=40, H=45)
  - Transformer_100 (ID: 1): X=0, Y=945 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=80, Y=945 (W=50, H=50)
  - Transformer_100 (ID: 1): X=130, Y=945 (W=40, H=45)
  - Transformer_100 (ID: 1): X=170, Y=945 (W=40, H=45)
  - Transformer_100 (ID: 1): X=210, Y=945 (W=40, H=45)
  - Water_Supply_100 (ID: 4): X=250, Y=945 (W=50, H=50)
  - Water_Supply_100 (ID: 4): X=300, Y=945 (W=50, H=50)
  """

DATA_STRING = DATA_STRING_SQUARE
NAME = 'Square'

def parse_data_string(data_string):
    """Parse the data string and extract component information."""
    pattern = r"- ([\w_]+) \(ID: (\d+)\): X=(\d+), Y=(\d+) \(W=(\d+), H=(\d+)\)"
    components = []
    
    for line in data_string.strip().split('\n'):
        match = re.search(pattern, line)
        if match:
            name, id_num, x, y, w, h = match.groups()
            components.append({
                'name': name,
                'id': int(id_num),
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h)
            })
    
    return components

def save_to_csv(components, filename="datacenter_"+NAME+".csv"):
    """Save the components data to a CSV file."""
    # Create the output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), '../output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create the full file path
    filepath = os.path.join(output_dir, filename)
    
    # Write the data to CSV
    with open(filepath, 'w', newline='') as csvfile:
        fieldnames = ['name', 'id', 'x', 'y', 'width', 'height']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for component in components:
            writer.writerow(component)
            
    return filepath

def visualize_layout(components):
    """Create a visualization of the datacenter layout."""
    # Determine figure size based on the max x and y coordinates
    max_x = max(comp['x'] + comp['width'] for comp in components)
    max_y = max(comp['y'] + comp['height'] for comp in components)
    
    # Create a color map for different component types
    component_types = set(comp['name'].split('_')[0] for comp in components)
    color_map = {
        'Data': 'blue',
        'Network': 'green',
        'Server': 'red',
        'Water': 'cyan',
        'Transformer': 'purple'
    }
    
    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(max_x/100 + 2, max_y/100 + 2))
    
    # Create a legend handles list
    legend_handles = []
    legend_names = []
    
    # Add each component as a rectangle
    for comp in components:
        component_type = comp['name'].split('_')[0]
        color = color_map.get(component_type, 'gray')
        
        # Add the rectangle
        rect = patches.Rectangle(
            (comp['x'], comp['y']),
            comp['width'], comp['height'],
            linewidth=1, edgecolor='black', facecolor=color, alpha=0.7
        )
        ax.add_patch(rect)
        
        # Add the component name in the center of the rectangle
        ax.text(
            comp['x'] + comp['width']/2,
            comp['y'] + comp['height']/2,
            comp['name'],
            ha='center', va='center',
            fontsize=8
        )
        
        # Add to legend if not already added
        if comp['name'] not in legend_names:
            legend_handles.append(patches.Patch(color=color, label=comp['name']))
            legend_names.append(comp['name'])
    
    # Set the axis limits and labels
    ax.set_xlim(-10, max_x + 10)
    ax.set_ylim(-10, max_y + 10)
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.set_title('Data Center ' + NAME + ' Layout')
    
    # Add a grid
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Add a legend with unique component types
    plt.legend(
        handles=[patches.Patch(color=color, label=ctype) for ctype, color in color_map.items() if ctype in component_types],
        loc='upper right',
        bbox_to_anchor=(1.1, 1)
    )
    
    # Save the figure
    output_dir = os.path.join(os.path.dirname(__file__), '../output')
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, "datacenter_layout.png"), dpi=300, bbox_inches='tight')
    
    # Show the figure
    plt.tight_layout()
    plt.show()

def main():
    # Parse the data string
    components = parse_data_string(DATA_STRING)
    
    # Save to CSV
    csv_path = save_to_csv(components)
    print(f"Data saved to CSV: {csv_path}")
    
    # Visualize the layout
    visualize_layout(components)

if __name__ == "__main__":
    main()
