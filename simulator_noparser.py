#!/usr/bin/env python

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


numpy.set_printoptions(suppress=True)

class Simulator(object):

    def __init__(self, 
        auto_observations=True, 
        auto_state = False, 
        uniform_init_belief =True,
        print_flag=True,
        policy_file='policy/default.policy', 
        pomdp_file='models/default.pomdp',
        pomdp_file_plus=None,
        policy_file_plus=None,
        trials_num=1,
        num_task=1, 
        num_patient=1,
        num_recipient=1,
        belief_threshold=0.7,
        ent_threshold=2):

        self.pomdp_file_plus=pomdp_file_plus
        self.policy_file_plus=policy_file_plus
        self.auto_observations = auto_observations
        self.auto_state = auto_state
        self.uniform_init_belief = uniform_init_belief
        self.print_flag = print_flag
        self.trials_num = trials_num
        self.belief_threshold = belief_threshold
        self.ent_threshold = ent_threshold

        self.num_task = num_task
        self.num_patient = num_patient
        self.num_recipient = num_recipient
        self.tablelist = conf.tablelist

        # to read the pomdp model
        model = pomdp_parser.Pomdp(filename=pomdp_file, parsing_print_flag=False)
        self.states = model.states
        #model_plus= pomdp_parser.Pomdp(filename='444_new.pomdp', parsing_print_flag=False)
        self.states_plus= None
        self.actions = model.actions
        self.observations = model.observations
        # print self.observations
        self.trans_mat = model.trans_mat
        self.obs_mat = model.obs_mat
        self.reward_mat = model.reward_mat

        # to read the learned policy
        self.policy = policy_parser.Policy(len(self.states), len(self.actions), 
            filename=policy_file)

        self.b = None   
        self.b_plus = None   
        self.a = None
        self.a_plus=None
        self.o = None
        self.o_plus= None
        # self.dialog_turn = 0

        numpy.set_printoptions(precision=2)

    #######################################################################
    def init_belief(self):

        if self.uniform_init_belief:
            self.b = numpy.ones(len(self.states)) / float(len(self.states))
                # print '\n',self.s, self.ct, self.b
        else:
            # here initial belief is sampled from a Dirichlet distribution
            self.b = numpy.random.dirichlet( numpy.ones(len(self.states)) )

        self.b = self.b.T

    ######################################################################

    def init_belief_plus(self):

        if self.uniform_init_belief:
            self.b_plus = numpy.ones(len(self.states_plus)) / float(len(self.states_plus))
                # print '\n',self.s, self.ct, self.b
        else:
            # here initial belief is sampled from a Dirichlet distribution
            self.b_plus = numpy.random.dirichlet( numpy.ones(len(self.states_plus)) )

        self.b_plus = self.b_plus.T

    ######################################################################
    def read_model_plus(self):
       
        # once its generated:
        # to read the pomdp model
        model = pomdp_parser.Pomdp(filename=self.pomdp_file_plus, parsing_print_flag=False) # probably filename needs to be changed to a better one avoiding conflicts
        self.states_plus = model.states
        self.actions_plus = model.actions
        self.observations_plus = model.observations
        # print self.observations
        self.trans_mat_plus = model.trans_mat
        self.obs_mat_plus = model.obs_mat
        self.reward_mat_plus = model.reward_mat

        self.policy_plus = policy_parser.Policy(len(self.states_plus), len(self.actions_plus), 
            filename=self.policy_file_plus)

    #####################################################################
    def get_action(self, string):
        i = 0
        for action in self.actions:
            if action == string:
                return i
            i += 1


    def get_action_plus(self, string):
        i = 0
        for action in self.actions_plus:
            if action == string:
                return i
            i += 1


    def action_to_text(self, string):
        if string == 'ask_p':
            return "What item should I bring?"
        elif string == 'ask_r':
            return "Who should I bring the item to?"
        
        match = None
        match = re.search('(?<=confirm_)\w*', string)
        if match:
            obsname = match.group(0)
            return "confirm " + obsname

    
    ######################################################################
    def get_full_request(self, cycletime):
        print self.observations # debug
        print "DEBUG: Full request here"

        # patient
        # get action from key
        self.a = self.get_action('ask_p')
        self.a_plus = self.get_action_plus('ask_p')

        # if auto observe, get initial request
        if self.auto_observations:
            rand = numpy.random.random_sample()
            acc = 0.0
            for i in range(len(self.observations_plus)):
                acc += self.obs_mat_plus[self.a_plus, self.s_plus, i]
                if acc > rand:
                    raw_str = self.observations_plus[i]
                    self.request_p = raw_str
                    break
            if raw_str == None:
                sys.exit('Error: observation no sampled properly')
        else:
            raw_str = raw_input("Input observation (patient/item): ")

        ''' Note: Should we have a random observation for unknown here too
        like we do for the later phases?  For now I have implemented it
        that way, which is different from how we do it in the standard 
        'simulator.py' file, where we just observe a known or we don't 
        observe at all '''

        self.observe(raw_str)
        # update for patient observation
        self.update(cycletime)
        # for belief plus
        self.update_plus(cycletime)

        # recipient
        # get action from key
        self.a = self.get_action('ask_r')
        self.a_plus = self.get_action_plus('ask_r')

        if self.auto_observations:
            rand = numpy.random.random_sample()
            acc = 0.0
            for i in range(len(self.observations_plus)):
                acc += self.obs_mat_plus[self.a_plus, self.s_plus, i]
                if acc > rand:
                    raw_str = self.observations_plus[i]
                    self.request_r = raw_str
                    break
            if raw_str == None:
                sys.exit('Error: observation no sampled properly')
        else:
            raw_str = raw_input("Input observation (recipient/person): ")
        
        self.observe(raw_str)
        # update for recipient observation
        self.update(cycletime)
        # for belief plus
        self.update_plus(cycletime)

##########################################################

    
    def add_new(self, raw_str):
        print "DEBUG: adding new"
        self.num_patient += 1
        self.num_recipient += 1
        self.b = self.b_plus
        self.states = self.states_plus
        self.actions = self.actions_plus
        self.s = self.s_plus
        self.observations = self.observations_plus
        self.trans_mat = self.trans_mat_plus
        self.obs_mat = self.obs_mat_plus
        self.reward_mat = self.reward_mat_plus
        self.policy = self.policy_plus

    #######################################################################
    def auto_observe(self):
        rand = numpy.random.random_sample()
        acc = 0.0
        for i in range(len(self.observations_plus)):
            acc += self.obs_mat_plus[self.a_plus, self.s_plus, i]
            if acc > rand:
                raw_str = self.observations_plus[i]
                self.request_p = raw_str
                break
        
        if raw_str == None:
            sys.exit('Error: observation no sampled properly')

        return raw_str

    def observe(self, ind):
        self.o = None
        print "OBSERVE:",ind

        for i in range(len(self.observations)):
            if self.observations[i] == ind:
                self.o = i

        if self.o == None:
            q_type = str(self.actions[self.a][-1])

            domain = [self.observations.index(o) for o in self.observations if q_type in o]
            #print domain
            self.o = numpy.random.choice(domain)
            #print self.o


    #######################################################################
    def update(self,cycletime):
        new_b = numpy.dot(self.b, self.trans_mat[self.a, :])
        new_b = [new_b[i] * self.obs_mat[self.a, i, self.o] for i in range(len(self.states))]

        # print 'sum of belief: ',sum(new_b)
        self.b = (new_b / sum(new_b)).T


    def update_plus(self,cycletime):
        #print self.actions_plus[self.a_plus]
        if self.actions_plus[self.a_plus] == "ask_r" or self.actions_plus[self.a_plus] == "ask_p":
            return

        new_b_plus = numpy.dot(self.b_plus, self.trans_mat_plus[self.actions_plus.index(self.actions[self.a]), :])
        new_b_plus = [new_b_plus[i] * self.obs_mat_plus[self.actions_plus.index(self.actions[self.a]), i, self.observations_plus.index(self.observations[self.o]),] for i in range(len(self.states_plus))]

        # print 'sum of belief: ',sum(new_b)
        self.b_plus = (new_b_plus / sum(new_b_plus)).T


    def entropy_check(self, entropy):
        if entropy > (0.40358 * self.num_patient + 0.771449):
            return True

        return False


    def get_marginal_edges(self, b, n, m):
        belief_rn = 0
        for i in range(m):
            belief_rn += self.b[n * i + n - 1]

        belief_pm = 0
        for i in range(n):
            belief_pm += self.b[n * (m - 1) + i]

        return belief_rn, belief_pm


    def belief_check(self):
        n = self.num_recipient + 1
        m = self.num_patient + 1

        belief_rn, belief_pm = self.get_marginal_edges(self.b_plus, n, m)

        print "DEBUG: Marginal rn = ",belief_rn
        print "DEBUG: Marginal pm = ",belief_pm

        if belief_rn > self.belief_threshold or belief_pm > self.belief_threshold:
            return True

        return False


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
                    if(inc_count > self.ent_threshold or self.belief_check()):
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
                print "REACHED CYCLE TIME 50"
                sys.exit(1)
                break

        return reward, cost, overall_reward, added

    #######################################################################
    def run_numbers_of_trials(self):

        cost_list = []
        success_list = []
        reward_list = []
        overall_reward_list = []
        
        # for new item or person
        true_positives = 0.0
        false_positives = 0.0
        true_negatives = 0.0
        false_negatives = 0.0

        string_i = ''
        string_p = ''
        string_r = ''

        # save initial values to reset before next run
        initial_num_recipient = self.num_recipient
        initial_num_patient = self.num_patient
        initial_states = self.states
        initial_actions = self.actions
        initial_observations = self.observations
        initial_trans_mat = self.trans_mat
        initial_obs_mat = self.obs_mat
        initial_reward_mat = self.reward_mat
        initial_policy = self.policy

        
        bar = Bar('Processing', max=self.trials_num)

        for i in range(self.trials_num):

            # seed random for experiments
            numpy.random.seed(i+2)

            # get a sample as the current state, terminal state exclusive
            if self.auto_state:
                # 50% chance fixed to select unknown state
                unknown_state = numpy.random.choice([True, False])

                if unknown_state == False:
                    self.s = numpy.random.randint(low=0, high=len(self.states)-1, size=(1))[0]
                    tuples = self.states[self.s].split('_')
                    ids = [int(tuples[0][1]),int(tuples[1][1]),int(tuples[2][1])]
                    self.s_plus = self.states_plus.index(self.states[self.s])
                else:
                    unknown_set = set(self.states_plus) - set(self.states)
                    unknown_set = list(unknown_set)
                    selected = numpy.random.choice(unknown_set)
                    self.s_plus = self.states_plus.index(selected)

            else:
                self.s_plus = int(input("Please specify the index of state: "))

            '''!!! important note: State self.s not used as goal anymore, since we need new items to be possible as well,
            instead self.s_plus is used to compare''' 

            #self.s_plus = self.states_plus.index(self.states[self.s])
            print self.states_plus[self.s_plus]
            print self.states
            if str(self.states_plus[self.s_plus]) in self.states:
                is_new = False
            else:
                is_new = True

            # run this episode and save the reward
            reward, cost, overall_reward, added = self.run()
            reward_list.append(reward)
            cost_list.append(cost)
            overall_reward_list.append(overall_reward)
 

            # use string based checking of success for now
            if (str(self.states_plus[self.s_plus]) in self.actions[self.a]) and (is_new == added):
                success_list.append(1.0)
            else:
                success_list.append(0.0)

            if is_new == True and added == True:
                true_positives += 1
            elif is_new == True and added == False:
                false_negatives += 1
            elif is_new == False and added == True:
                false_positives += 1
            elif is_new == False and added == False:
                true_negatives += 1

            # reset for next run

            self.num_patient = initial_num_patient
            self.num_recipient = initial_num_recipient
            self.num_recipient = initial_num_recipient
            self.num_patient = initial_num_patient
            self.states = initial_states
            self.actions = initial_actions
            self.observations = initial_observations
            self.trans_mat = initial_trans_mat
            self.obs_mat = initial_obs_mat
            self.reward_mat = initial_reward_mat
            self.policy = initial_policy

            bar.next()

        bar.finish()

        cost_arr = numpy.array(cost_list)
        success_arr = numpy.array(success_list)
        reward_arr = numpy.array(reward_list)
        overall_reward_arr = numpy.array(overall_reward_list)

        print('average cost: ' + str(numpy.mean(cost_arr))[1:] + \
            ' with std ' + str(numpy.std(cost_arr)))
        print('average success: ' + str(numpy.mean(success_arr)) + \
            ' with std ' + str(numpy.std(success_arr)))
        print('average reward: ' + str(numpy.mean(reward_arr)) + \
            ' with std ' + str(numpy.std(reward_arr)))
        print('average overall reward: ' + str(numpy.mean(overall_reward_arr)) + \
            ' with std ' + str(numpy.std(overall_reward_arr)))

        print('True positives (%):' + str(true_positives))
        print('False positives (%):' + str(false_positives))
        print('True negatives (%):' + str(true_negatives))
        print('False negatives (%):' + str(false_negatives))

        precision = true_positives/(true_positives + false_positives)
        recall = true_positives/(true_positives + false_negatives)
        print('Precision:' + str(precision))
        print('Recall:' + str(recall))

        return (numpy.mean(cost_arr), numpy.mean(success_arr), \
            numpy.mean(overall_reward_arr), precision, recall)



