import os
import json

import callflow

LOGGER = callflow.get_logger(__name__)


class BaseCallFlow:
    def __init__(self, config={}, process=False):

        # Assert if config is provided.
        assert config != None

        # Convert config json to props. Never touch self.config ever.
        self.props = json.loads(json.dumps(config, default=lambda o: o.__dict__))

        # Based on option, either process into .callflow or read from .callflow.
        if process:
            self._create_dot_callflow_folder()
            self.process_datasets()
        else:
            self.datasets = self.read_datasets()

    # --------------------------------------------------------------------------
    # public API. child classes should implement these functions
    def process_datasets(self):
        self._process_datasets()

    def read_datasets(self):
        return self._read_datasets()

    def request(self, operation):
        return self._request(operation)

    # --------------------------------------------------------------------------
    def displayStats(self, name):
        """
        TODO: Probably remove. 
        """
        log.warn("==========================")
        log.info("Number of datasets : {0}".format(len(self.config[name].paths.keys())))
        log.info("Stats: Dataset ({0}) ".format(name))
        log.warn("==========================")
        max_inclusive_time = utils.getMaxIncTime(gf)
        max_exclusive_time = utils.getMaxExcTime(gf)
        avg_inclusive_time = utils.getAvgIncTime(gf)
        avg_exclusive_time = utils.getAvgExcTime(gf)
        num_of_nodes = utils.getNumOfNodes(gf)
        log.info("[] Rows in dataframe: {0}".format(self.states[name].df.shape[0]))
        log.info("Max Inclusive time = {0} ".format(max_inclusive_time))
        log.info("Max Exclusive time = {0} ".format(max_exclusive_time))
        log.info("Avg Inclusive time = {0} ".format(avg_inclusive_time))
        log.info("Avg Exclusive time = {0} ".format(avg_exclusive_time))
        log.info("Number of nodes in CCT = {0}".format(num_of_nodes))

    # --------------------------------------------------------------------------
    def _create_dot_callflow_folder(self):
        """
        Create a .callflow directory and empty files.
        """
        LOGGER.debug(f"Saved .callflow directory is: {self.props['save_path']}")

        if not os.path.exists(self.props["save_path"]):
            os.makedirs(self.props["save_path"])

        for dataset in self.props["datasets"]:
            dataset_dir = os.path.join(self.props["save_path"], dataset["name"])
            LOGGER.debug(dataset_dir)
            if not os.path.exists(dataset_dir):
                # if self.debug:
                LOGGER.debug(
                    f"Creating .callflow directory for dataset : {dataset['name']}"
                )
                os.makedirs(dataset_dir)

            files = [
                "entire_df.csv",
                "filter_df.csv",
                "entire_nxg.json",
                "filter_nxg.json",
            ]
            for f in files:
                fname = os.path.join(dataset_dir, f)
                if not os.path.exists(fname):
                    open(fname, "w").close()

    # --------------------------------------------------------------------------
