# Defined as a generic bot, can use multiple models

from conversions.input_formatter import InputFormatter
import importlib
import inspect
from modelHelpers import action_handler
from modelHelpers import reward_manager
from models.actor_critic import policy_gradient

import numpy as np
import random
import tensorflow as tf

MODEL_CONFIGURATION_HEADER = 'Model Configuration'

class Agent:
    model_class = None
    previous_reward = 0
    previous_action = None
    previous_score = 0
    previous_enemy_goals = 0
    previous_owngoals = 0

    def __init__(self, name, team, index, config_file=None):
        self.config_file = config_file
        self.index = index
        self.load_config_file()
        self.inp = InputFormatter(team, index)
        self.reward_manager = reward_manager.RewardManager()
        config = tf.ConfigProto(
            device_count={'GPU': 0}
        )
        self.sess = tf.Session(config=config)
        #self.sess = tf.Session()
        writer = tf.summary.FileWriter('tmp/{}-experiment'.format(random.randint(0, 1000000)))
        self.actions_handler = action_handler.ActionHandler(split_mode=True)
        self.state_dim = self.inp.get_state_dim_with_features()
        self.num_actions = self.actions_handler.get_action_size()
        print('num_actions', self.num_actions)
        self.model = self.get_model_class()(self.sess,
                                            self.state_dim,
                                            self.num_actions,
                                            action_handler=self.actions_handler,
                                            summary_writer=writer)
        self.model.initialize_model()

    def load_config_file(self):
        if self.config_file is None:
            return
        #read file code here

        model_package = self.config_file.get(MODEL_CONFIGURATION_HEADER,
                                                   'model_package')
        model_name = self.config_file.get(MODEL_CONFIGURATION_HEADER,
                                                 'model_name')
        print('getting model from', model_package)
        print('name of model', model_name)
        model_package = importlib.import_module(model_package)
        module_classes = inspect.getmembers(model_package,  inspect.isclass)
        for class_group in module_classes:
            if class_group[0] == model_name:
                self.model_class = class_group[1]
        if self.model_class is not None:
            self.model_class.config_file = self.config_file


    def get_model_class(self):
        if self.model_class is None:
            print('Invalid model using default')
            return policy_gradient.PolicyGradient
        else:
            return self.model_class

    def get_reward(self, input_state):
        reward = self.reward_manager.get_reward(input_state)
        return reward

    def get_output_vector(self, game_tick_packet):
        input_state, features = self.inp.create_input_array(game_tick_packet)
        input_state = np.append(input_state, features)
        if self.state_dim != len(input_state):
            print('wrong input size', self.index, len(input_state))
            return self.actions_handler.create_controller_from_selection(
                self.actions_handler.get_random_option()) # do not return anything

        if self.model.is_training:
            reward = self.get_reward(input_state)

            if self.previous_action is not None:
                self.model.store_rollout(input_state, self.previous_action, reward)

        action = self.model.sample_action(np.array(input_state).reshape((1, -1)))
        if action is None:
            print("invalid action no type returned")
            action = self.actions_handler.get_random_option()
        self.previous_action = action
        return self.actions_handler.create_controller_from_selection(action)
