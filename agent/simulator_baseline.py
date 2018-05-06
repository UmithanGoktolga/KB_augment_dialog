from simulator_noparser import Simulator
import sys
import time
import pomdp_generator
import pomdp_parser
import policy_parser
import readline
import numpy
import random
from scipy import stats
from progress.bar import Bar
import subprocess
import conf
import re
import os
import string
import time
import ast

class Baseline(Simulator):

    def run(self):
        cost = 0.0
        self.init_belief()
        self.init_belief_plus()

        reward = 0.0
        overall_reward = 0.0

        cycletime = 0

        current_entropy = float("inf")
        old_entropy = float("inf")
        inc_count = 0
        added = False

        while True:
            cycletime += 1

            # print self.b

            if self.print_flag:
                print('\tstate:\t' + self.states_plus[self.s_plus] + ' ' + str(self.s_plus))
                print('\tcost so far:\t' + str(cost))

            # select action
            # entropy
            old_entropy = current_entropy
            current_entropy = stats.entropy(self.b)
            current_entropy_plus = stats.entropy(self.b_plus)
            print "DEBUG: Entropy = ",current_entropy
            print "DEBUG: Entropy_plus = ",current_entropy_plus
            # check if entropy increased
            if (old_entropy < current_entropy):
                inc_count += 1
                print "DEBUG: entropy increased"

            if(self.entropy_check(current_entropy)):
                self.get_full_request(cycletime)
                if self.print_flag:
                    print('\n\tbelief:\t\t' + str(self.b))

                if self.print_flag:
                    print('\n\tbelief_plus:\t' + str(self.b_plus))
            else:
                done = False
                self.a = int(self.policy.select_action(self.b))
                self.a_plus = self.actions_plus.index(self.actions[self.a])
            
                if self.print_flag:
                    print('\taction:\t' + self.actions[self.a] + ' ' + str(self.a))

                    print 'num_recipients', self.num_recipient
                    print 'num_patients', self.num_patient

                    question = self.action_to_text(self.actions[self.a])
                    if question:
                        print('QUESTION: ' + question)
                    elif ('go' in self.actions[self.a]):
                        print('EXECUTE: ' + self.actions[self.a])
                        done = True


                if done == True:
                    overall_reward += self.reward_mat_plus[self.a_plus, self.s_plus]
                    break

                if self.auto_observations:
                    raw_str = self.auto_observe()
                else:
                    raw_str = raw_input("Input observation: ")

                # check entropy increases arbitrary no of times for now
                if (added == False):
                    if(cycletime > 15):
                        if (self.actions[self.a] == "ask_p" or self.actions[self.a] == "ask_r"):
                            print "--- new item/person ---"
                            added = True
                            self.add_new(raw_str)

                self.observe(raw_str)
                if self.print_flag:
                    print('\tobserve:\t'+self.observations[self.o]+' '+str(self.o))

                self.update(cycletime)
                if self.print_flag:
                    print('\n\tbelief:\t\t' + str(self.b))
                self.update_plus(cycletime)
                if self.print_flag:
                    print('\n\tbelief_plus:\t' + str(self.b_plus))


            overall_reward += self.reward_mat_plus[self.a_plus, self.s_plus]
            # print('current cost: ' + str(self.reward_mat[self.a, self.s]))
            # print('overall cost: ' + str(overall_reward))

            if 'go' in self.actions_plus[self.a_plus]:
                # print '--------------------',
                if self.print_flag is True:
                    print('\treward: ' + str(self.reward_mat_plus[self.a_plus, self.s_plus]))
                reward += self.reward_mat_plus[self.a_plus, self.s_plus]
                break
            else:
                cost += self.reward_mat_plus[self.a_plus, self.s_plus]

            if cycletime == 50:
                cost += self.reward_mat_plus[self.a_plus, self.s_plus]
                print "BASELINE: REACHED CYCLE TIME 50"
                sys.exit(1)
                break

        return reward, cost, overall_reward, added