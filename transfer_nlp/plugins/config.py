"""
This file contains all necessary plugins classes that the framework will use to let a user interact with custom models, data loaders, etc...

The Registry pattern used here is inspired from this post: https://realpython.com/primer-on-python-decorators/
"""
import abc
import inspect
import json
import logging
from abc import abstractmethod, ABC
from pathlib import Path
from typing import Dict, Union, Any, Optional

import ignite.metrics as metrics
import torch.nn as nn
import torch.optim as optim
from smart_open import open

logger = logging.getLogger(__name__)

CLASSES = {
    'CrossEntropyLoss': nn.CrossEntropyLoss,
    'BCEWithLogitsLoss': nn.BCEWithLogitsLoss,
    "Adam": optim.Adam,
    "SGD": optim.SGD,
    "AdaDelta": optim.Adadelta,
    "AdaGrad": optim.Adagrad,
    "SparseAdam": optim.SparseAdam,
    "AdaMax": optim.Adamax,
    "ASGD": optim.ASGD,
    "LBFGS": optim.LBFGS,
    "RMSPROP": optim.RMSprop,
    "Rprop": optim.Rprop,
    "ReduceLROnPlateau": optim.lr_scheduler.ReduceLROnPlateau,
    "MultiStepLR": optim.lr_scheduler.MultiStepLR,
    "ExponentialLR": optim.lr_scheduler.ExponentialLR,
    "CosineAnnealingLR": optim.lr_scheduler.CosineAnnealingLR,
    "LambdaLR": optim.lr_scheduler.LambdaLR,
    "ReLU": nn.functional.relu,
    "LeakyReLU": nn.functional.leaky_relu,
    "Tanh": nn.functional.tanh,
    "Softsign": nn.functional.softsign,
    "Softshrink": nn.functional.softshrink,
    "Softplus": nn.functional.softplus,
    "Sigmoid": nn.Sigmoid,
    "CELU": nn.CELU,
    "SELU": nn.functional.selu,
    "RReLU": nn.functional.rrelu,
    "ReLU6": nn.functional.relu6,
    "PReLU": nn.functional.prelu,
    "LogSigmoid": nn.functional.logsigmoid,
    "Hardtanh": nn.functional.hardtanh,
    "Hardshrink": nn.functional.hardshrink,
    "ELU": nn.functional.elu,
    "Softmin": nn.functional.softmin,
    "Softmax": nn.functional.softmax,
    "LogSoftmax": nn.functional.log_softmax,
    "GLU": nn.functional.glu,
    "TanhShrink": nn.functional.tanhshrink,
    "Accuracy": metrics.Accuracy,
}


def register_plugin(clazz):
    if clazz.__name__ in CLASSES:
        raise ValueError(f"{clazz.__name__} is already registered to class {CLASSES[clazz.__name__]}. Please select another name")
    else:
        CLASSES[clazz.__name__] = clazz
        return clazz


class UnconfiguredItemsException(Exception):
    def __init__(self, items):
        super().__init__(f'There are some unconfigured items, which makes these items not configurable: {items}')
        self.items = items

class ConfigFactoryABC(ABC):

    @abstractmethod
    def create(self):
        pass

class ParamFactory(ConfigFactoryABC):

    def __init__(self, param):
        self.param = param

    def create(self):
        return self.param


class PluginFactory(ConfigFactoryABC):

    def __init__(self, cls, param2config_key: Optional[Dict[str, str]], *args, **kwargs):
        self.cls = cls
        self.param2config_key = param2config_key
        self.args = args
        self.kwargs = kwargs

    def create(self):
        return self.cls(*self.args, **self.kwargs)

class ExperimentConfig:

    def __init__(self, experiment: Union[str, Path, Dict], **env):
        """
        :param experiment: the experiment config
        :param env: substitution variables, e.g. a HOME directory. generally use all caps.
        :return: the experiment
        """
        self.factories: Dict[str, ConfigFactoryABC] = {}
        self.experiment: Dict[str, Any] = None

        env_keys = sorted(env.keys(), key=lambda k: len(k), reverse=True)

        def do_env_subs(v: Any) -> str:
            v_upd = v
            if isinstance(v_upd, str):
                for env_key in env_keys:
                    v_upd = v_upd.replace(env_key, env[env_key])

                if v_upd != v:
                    logger.info('*** updating parameter %s -> %s', v, v_upd)

            return v_upd

        if isinstance(experiment, dict):
            config = dict(experiment)
        else:
            config = json.load(open(experiment))

        # extract simple parameters
        logger.info(f"Initializing simple parameters:")
        experiment = {}
        for k, v in config.items():
            if not isinstance(v, dict) and not isinstance(v, list):
                logger.info(f"Parameter {k}: {v}")
                v = do_env_subs(v)
                experiment[k] = v
                self.factories[k] = ParamFactory(v)

        # extract simple lists
        logger.info(f"Initializing simple lists:")
        for k, v in config.items():
            if isinstance(v, list) and all(not isinstance(vv, dict) and not isinstance(vv, list) for vv in v):
                logger.info(f"Parameter {k}: {v}")
                upd = []
                for vv in v:
                    upd.append(do_env_subs(vv))
                experiment[k] = upd
                self.factories[k] = PluginFactory(list, None, upd)

        for k in experiment:
            del config[k]

        try:
            logger.info(f"Initializing complex configurations ignoring default params:")
            self._build_items(config, experiment, 0)
        except UnconfiguredItemsException as e:
            pass

        try:
            logger.info(f"Initializing complex configurations only filling in default params not found in the experiment:")
            self._build_items(config, experiment, 1)
        except UnconfiguredItemsException as e:
            pass

        try:
            logger.info(f"Initializing complex configurations filling in all default params:")
            self._build_items(config, experiment, 2)
        except UnconfiguredItemsException as e:
            logging.error('There are unconfigured items in the experiment. Please check your configuration:')
            for k, v in e.items.items():
                logging.error(f'"{k}" missing properties:')
                for vv in v:
                    logging.error(f'\t+ {vv}')

            raise e

        self.experiment = experiment


    def _build_items(self, config: Dict[str, Any], experiment: Dict[str, Any], default_params_mode: int):
        """

        :param config:
        :param experiment:
        :param default_params_mode: 0 - ignore default params, 1 - only fill in default params not found in the experiment, 2 - fill in all default params
        :return: None
        :raise UnconfiguredItemsException: if items are unable to be configured
        """
        i = 1
        while config:
            logger.info(f"Pass {i}")
            i += 1
            configured = set()  # items configured in this iteration
            unconfigured = {}  # items unable to be configured in this iteration
            for k, v in config.items():
                logger.info(f"Parameter {k}")
                if not isinstance(v, dict):
                    raise ValueError(f'complex configuration object config[{k}] must be a dict')

                if '_name' not in v:
                    raise ValueError(f'complex configuration object config[{k}] must be have a "_name" property')

                clazz = CLASSES.get(v['_name'])
                if not clazz:
                    raise ValueError(
                        f'config[{k}] is named {v["_name"]} but this name is not registered. see transfer_nlp.config.register_plugin for more information')

                spec = inspect.getfullargspec(clazz.__init__)
                params = {}
                param2config_key = {}
                named_params = {p: pv for p, pv in v.items() if p != '_name'}
                default_params = {p: pv for p, pv in zip(reversed(spec.args), reversed(spec.defaults))} if spec.defaults else {}

                literal_params = {}
                for p, pv in v.items():
                    if p[-1] == '_':
                        literal_params[p[:-1]] = pv
                    elif isinstance(pv, list):
                        for pvv in pv:
                            if not isinstance(pvv, str):
                                raise ValueError(
                                    f'string required for parameter names in list paramters...use key_ notation "{p}_" if you want to specify a literal parameter values.')

                    elif not isinstance(pv, str):
                        raise ValueError(f'string required for parameter names...use key_ notation "{p}_" if you want to specify a literal parameter value.')

                for arg in spec.args[1:]:
                    if arg in literal_params:
                        params[arg] = literal_params[arg]
                        param2config_key[arg] = None
                    else:
                        if arg == 'experiment_config':
                            params[arg] = self
                            param2config_key[arg] = arg
                        if arg in named_params:
                            alias = named_params[arg]
                            if isinstance(alias, list):
                                param_list = []
                                for p in alias:
                                    if p in experiment:
                                        param_list.append(experiment[p])
                                    else:
                                        break
                                if len(param_list) == len(alias):
                                    params[arg] = param_list
                            elif alias in experiment:
                                params[arg] = experiment[alias]
                            param2config_key[arg] = alias
                        elif arg in experiment:
                            params[arg] = experiment[arg]
                            param2config_key[arg] = arg
                        elif default_params_mode == 1 and arg not in config and arg in default_params:
                            params[arg] = default_params[arg]
                            param2config_key[arg] = None
                        elif default_params_mode == 2 and arg in default_params:
                            params[arg] = default_params[arg]
                            param2config_key[arg] = None

                if len(params) == len(spec.args) - 1:
                    experiment[k] = clazz(**params)
                    self.factories[k] = PluginFactory(cls=clazz, param2config_key=param2config_key, **params)
                    configured.add(k)
                else:
                    unconfigured[k] = {arg for arg in spec.args[1:] if arg not in params}

            if configured:
                for k in configured:
                    del config[k]
            else:
                if config:
                    raise UnconfiguredItemsException(unconfigured)

    def _check_init(self):
        if self.experiment is None:
            raise ValueError('experiment config is not setup yet!')

    # map-like methods
    def __getitem__(self, item):
        self._check_init()
        return self.experiment[item]

    def get(self, item, default=None):
        self._check_init()
        return self.experiment.get(item, default)

    def __iter__(self):
        self._check_init()
        return iter(self.experiment)

    def items(self):
        self._check_init()
        return self.experiment.items()

    def values(self):
        self._check_init()
        return self.experiment.values()

    def keys(self):
        self._check_init()
        return self.experiment.keys()

    def __setitem__(self, key, value):
        raise ValueError("cannot update experiment!")
