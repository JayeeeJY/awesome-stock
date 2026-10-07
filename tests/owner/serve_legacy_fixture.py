"""Legacy browser regression fixture only; never a production entrypoint."""
import argparse
from pathlib import Path
import sys
from wsgiref.simple_server import make_server
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend/src'))
from awesome_stock.runtime.owner import application
from awesome_stock.runtime.server import QuietRequestHandler
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--data-dir', type=Path, required=True)
args = parser.parse_args()
app = application(port=args.port, data_dir=args.data_dir)
with make_server('127.0.0.1', args.port, app, handler_class=QuietRequestHandler) as server:
    server.serve_forever()
