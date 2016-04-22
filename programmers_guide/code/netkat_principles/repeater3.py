import sys, logging
import frenetic
from frenetic.syntax import *

class RepeaterApp3(frenetic.App):

  client_id = "repeater"

  def connected(self):
    def handle_current_switches(switches):
      logging.info("Connected to Frenetic - Switches: "+str(switches))
    self.current_switches(callback=handle_current_switches)

logging.basicConfig(stream = sys.stderr, \
  format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO \
)
app = RepeaterApp3()
app.start_event_loop()
