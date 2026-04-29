import logging
import os
import time
from pathlib import Path

# Configure file-based logging for metrics
# Path: config/metrics.py -> parent -> multi_agent_system -> parent -> 02_code
log_dir = Path(__file__).parent.parent.parent / "metrics"
log_dir.mkdir(parents=True, exist_ok=True)

run_tag = os.getenv("SIM_RUN_TAG", "run")
timestamp = time.strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"metrics_{run_tag}_{timestamp}.log"

file_handler = logging.FileHandler(log_file, mode="w")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)

logger = logging.getLogger("metrics")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(console_handler)


class MetricsTracker:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.loop_count = 0
        self.start_time = time.time()
        self.end_time = None
        self._finalized = False

    def add_tokens(self, input_tokens: int, output_tokens: int):
        """Record token usage"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        total = input_tokens + output_tokens
        logger.info(f"Tokens - Input: {input_tokens}, Output: {output_tokens}, Total: {total}")

    def record_loop(self):
        """Increment loop counter"""
        self.loop_count += 1
        logger.info(f"Loop {self.loop_count} completed")

    def end_simulation(self):
        """End simulation and log summary"""
        if self._finalized:
            return  # Only run once
        
        self._finalized = True
        self.end_time = time.time()
        runtime = self.end_time - self.start_time
        
        logger.info("\n" + "=" * 70)
        logger.info("SIMULATION METRICS")
        logger.info("=" * 70)
        logger.info(f"Total Loops: {self.loop_count}")
        logger.info(f"Total Messages: {self.loop_count * 4}")
        logger.info(f"Input Tokens: {self.total_input_tokens}")
        logger.info(f"Output Tokens: {self.total_output_tokens}")
        logger.info(f"Total Tokens: {self.total_input_tokens + self.total_output_tokens}")
        logger.info(f"Runtime: {runtime:.2f}s")
        logger.info("=" * 70 + "\n")


metrics = MetricsTracker()
logger.info("Metrics tracker initialized")
