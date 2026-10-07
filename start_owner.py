"""Start the single-owner Community ledger candidate."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'backend/src'))
from awesome_stock.runtime.owner import main
if __name__=='__main__':main()
