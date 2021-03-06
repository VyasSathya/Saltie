from conversions import output_formatter
from conversions.input_formatter import get_state_dim_with_features
from modelHelpers import action_handler
from modelHelpers import feature_creator
from models.atbas import rnn_atba
from models.actor_critic import base_actor_critic
from models.atbas import nnatba

import numpy as np
import tensorflow as tf


class CopyTrainer:
    learning_rate = 0.3

    file_number = 0

    epoch = 0
    display_step = 5

    batch_size = 1000
    input_game_tick = []
    input_batch = []
    label_batch = []

    def __init__(self):
        #config = tf.ConfigProto(
        #    device_count={'GPU': 1}
        #)
        #self.sess = tf.Session(config=config)
        self.sess = tf.Session()
        # writer = tf.summary.FileWriter('tmp/{}-experiment'.format(random.randint(0, 1000000)))

        self.action_handler = action_handler.ActionHandler(split_mode=True)

        self.state_dim = get_state_dim_with_features()
        print('state size ' + str(self.state_dim))
        self.num_actions = self.action_handler.get_action_size()
        self.agent = self.get_model()(self.sess, self.state_dim, self.num_actions, self.action_handler, is_training=True, optimizer=tf.train.AdamOptimizer())

        self.loss, self.input, self.label = self.agent.create_copy_training_model(batch_size=self.batch_size)

        if self.agent.train_op is None:
            self.agent.train_op = tf.train.GradientDescentOptimizer(self.learning_rate).minimize(self.loss)
        self.agent.initialize_model()

    def get_model(self):
        #return rnn_atba.RNNAtba
        #return nnatba.NNAtba
        return base_actor_critic.BaseActorCritic

    def start_new_file(self):
        self.file_number += 1
        self.input_batch = []
        self.label_batch = []
        self.input_game_tick = []

    def add_pair(self, input_array, output_array):
        if len(input_array) == 193:
            input_array = np.append(input_array, [0])
            input_array = np.append(input_array, [0])

        extra_features = feature_creator.get_extra_features_from_array(input_array)

        input = np.append(input_array, extra_features)
        self.input_batch.append(input)

        label = self.action_handler.create_action_label(output_array)
        #print(label)
        self.label_batch.append(label)

    def process_pair(self, input_array, output_array, pair_number, file_version):
        self.add_pair(input_array, output_array)
        if len(self.input_batch) == self.batch_size:
            self.batch_process()
            self.input_batch = []
            self.label_batch = []
            self.input_game_tick = []
            # do stuff

    def batch_process(self):
        if len(self.input_batch) == 0 or len(self.label_batch) == 0:
            print('batch was empty quitting')
            return

        self.input_batch = np.array(self.input_batch)
        self.input_batch = self.input_batch.reshape(len(self.input_batch), self.state_dim)

        self.label_batch = np.array(self.label_batch)
        self.label_batch = self.label_batch.reshape(len(self.label_batch), self.num_actions)

        _, c = self.sess.run([self.agent.train_op, self.loss], feed_dict={self.input: self.input_batch, self.label: self.label_batch})
        # Display logs per step
        if self.epoch % self.display_step == 0:
            print("File:", '%04d' % self.file_number, "Epoch:", '%04d' % (self.epoch+1),
                  "cost= " + str(c))
        self.epoch += 1

    def end_file(self):
        self.batch_process()
        if self.file_number % 3 == 0:
            saver = tf.train.Saver()
            file_path = self.agent.get_model_path(self.agent.get_default_file_name() + str(self.file_number) + ".ckpt")
            saver.save(self.sess, file_path)

    def end_everything(self):
        saver = tf.train.Saver()
        file_path = self.agent.get_model_path(self.agent.get_default_file_name() + ".ckpt")
        saver.save(self.sess, file_path)
