import sys
import os
import ast
from threading import Thread, current_thread
from subprocess import Popen, PIPE
import socket
import arcade
import argparse
import time
import uuid
import json
from datetime import datetime
import simulation
from arcade import set_window, run, close_window
import asyncio
import websockets
import functools
from run import trim_cmd
# import cProfile


EXP_D_T = datetime.now().strftime("%d-%m-%Y_%H_%M_%S")

async def threaded_client(reply, ws, sim_instances, ARENA_WIDTH, ARENA_HEIGHT, name_of_experiment,  SWARM_SIZE, run_time,
                         INPUT_TIME, GRID_X, GRID_Y, exp_type, disaster_size, disaster_location, operator_size,
                         operator_location,reliability_1, reliability_2, unreliability_percentage, moving_disaster,
                         communication_noise, alpha, normal_command, command_period, constant_repulsion,
                         operator_vision_radius,communication_range, vision_range, velocity_weight_coef, boundary_repulsion,
                         aging_factor, gp, gp_step, maze, through_walls,communication_noise_strength, communication_noise_prob,
                         positioning_noise_strength, positioning_noise_prob,sensing_noise_strength, sensing_noise_prob):

    await ws.send(json.dumps({"operation": "start", "timesteps": run_time}))

    sim_id = reply['id']
    process = Popen([sys.executable, "simulation.py"] 
                    + trim_cmd(" -sim_id " + str(sim_id) + " -width " + str(ARENA_WIDTH) + " -height " + str(ARENA_HEIGHT) \
                               + " -name " + name_of_experiment + " -size " + str(SWARM_SIZE) + " -run_time " + str(run_time) \
                               + " -input_time " + str(INPUT_TIME) + " -alpha " + str(alpha) + " -hum_r " + str(operator_vision_radius) \
                               + " -vis_range " + str(vision_range) + " -comm_range " + str(communication_range)), stdin=PIPE, stdout=PIPE)
    sim_instances[sim_id] = process
    
    # the map to get the score from
    # print(sim.operator_list[0].confidence_map)
    await ws.send(json.dumps({"operation": "close", "score": 0}))

    while True:
        try:
            message = await ws.recv()
            print('Received message from server: ' + str(message))
            message_data = json.loads(message)
            
            if message_data["operation"] == "update":
                x_change = message_data["pos"][0]
                y_change = message_data["pos"][1]
                instance = sim_instances[sim_id]
                
                if message_data["action"] == "attract":
                    instance.stdin.flush()
                    cmd = '{},{},{}\n'.format("attract", str(x_change), str(y_change))
                    instance.stdin.write(cmd.encode())
                elif message_data["action"] == "deflect":
                    instance.stdin.flush()
                    cmd = '{},{},{}\n'.format("deflect", str(x_change), str(y_change))
                    instance.stdin.write(cmd.encode())  
            elif message_data["operation"] == "close":
                instance = sim_instances[sim_id]
                instance.stdin.flush()
                instance.stdin.write('close\n'.encode())
                break
        except websockets.exceptions.ConnectionClosed:
            instance = sim_instances[sim_id]
            instance.stdin.flush()
            instance.stdin.write('close\n'.encode())
            process.terminate()
            print('Connection with server closed')
            break


# Simply collects the belief error and the confidence of the swarm at each 5 steps
# Could be used with different swarm sizes, reliability ranges and percentages, and communication noise
def init(SWARM_SIZE = 15, ARENA_WIDTH = 600, ARENA_HEIGHT = 600, name_of_experiment = EXP_D_T, run_time = 10, INPUT_TIME = 300, GRID_X = 40, GRID_Y = 40,
               disaster_size = 1, disaster_location = 'random', operator_size = 1, operator_location = 'random', reliability = (100, 101), unreliability_percentage = 0, 
               moving_disaster = False, communication_noise = 0, alpha = 10, normal_command = None, command_period = 0, constant_repulsion = False, 
               operator_vision_radius = 150, communication_range = 8, vision_range = 2, velocity_weight_coef = 0.01, boundary_repulsion = 1, aging_factor = 0.9999,
               gp = False, gp_step = 50, maze = None, through_walls = True, communication_noise_strength = 0, communication_noise_prob = 0, positioning_noise_strength = 0,
               positioning_noise_prob = 0, sensing_noise_strength = 0, sensing_noise_prob = 0, exp_type = None):

    clients = {}
    async def start_listen(websocket, path, name_of_experiment):
        jsondata = await websocket.recv()
        reply = json.loads(jsondata)

        if reply['operation'] == 'start':
            clients[reply['id']] = websocket

            print(clients)

            sim_instances = {}
            if name_of_experiment == EXP_D_T:
                name_of_experiment = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")

            await threaded_client(reply, websocket, sim_instances, ARENA_WIDTH, ARENA_HEIGHT, name_of_experiment,  SWARM_SIZE, run_time,
                        INPUT_TIME, GRID_X, GRID_Y, exp_type, disaster_size, disaster_location, operator_size,
                        operator_location,reliability[0], reliability[1], unreliability_percentage, moving_disaster,
                        communication_noise, alpha, normal_command, command_period, constant_repulsion,
                        operator_vision_radius,communication_range, vision_range, velocity_weight_coef, boundary_repulsion,
                        aging_factor, gp, gp_step, maze, through_walls,communication_noise_strength, communication_noise_prob,
                        positioning_noise_strength, positioning_noise_prob,sensing_noise_strength, sensing_noise_prob)

        else:
            print(reply)


    if exp_type == "normal_network": # In case we have an online experience
        print("start web socket server")
        start_server = websockets.serve(functools.partial(start_listen, name_of_experiment=name_of_experiment), "localhost", 8765)

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
        
    else:
        sim = simulation.SwarmSimulator(ARENA_WIDTH, ARENA_HEIGHT, name_of_experiment,  SWARM_SIZE, run_time, INPUT_TIME, GRID_X, GRID_Y, exp_type)
        sim.setup(disaster_size, disaster_location, operator_size, operator_location, reliability[0], reliability[1], unreliability_percentage, 
                   moving_disaster, communication_noise, alpha, normal_command, command_period, constant_repulsion, operator_vision_radius,
                   communication_range, vision_range, velocity_weight_coef, boundary_repulsion, aging_factor, gp, gp_step, maze, through_walls,
                   communication_noise_strength, communication_noise_prob, positioning_noise_strength, positioning_noise_prob,sensing_noise_strength, sensing_noise_prob)

        if not os.path.isdir('outputs'):
            os.mkdir('outputs')
        if (not os.path.isdir('outputs/' + name_of_experiment)):
            os.mkdir('outputs/' + name_of_experiment)
        if (not os.path.isdir('outputs/' + name_of_experiment + "/" + str(EXP_D_T))):
            os.mkdir('outputs/' + name_of_experiment + "/" + str(EXP_D_T))
        if (not os.path.isdir('outputs/' + name_of_experiment + "/" + str(EXP_D_T) + '/performance_test')):
            os.mkdir('outputs/' + name_of_experiment + "/" + str(EXP_D_T) + '/performance_test')
            
        sim.directory = str('outputs/' + name_of_experiment + "/" + str(EXP_D_T))

        directory = sim.directory
            
        sim.log_setup(directory)   
        if exp_type == "user_study_2":
            sim.set_visible(False)

        try:
            arcade.run()              
            # cProfile.run('arcade.run()')    
            
            
            #sim.plot_heatmaps(sim.random_drone_confidence_maps, 'Random drone confidence')
            #sim.plot_heatmaps(sim.random_drone_belief_maps, 'Random drone belief')
            
            #sim.plot_boxplots(sim.swarm_confidence, 'Swarm confidence over time')
            #sim.plot_boxplots(sim.swarm_internal_error, 'Swarm belief map error over time')
            
            #sim.plot_heatmaps(sim.operator_confidence_maps, 'Operator confidence')
            #sim.plot_heatmaps(sim.operator_belief_maps, 'Operator belief')
            
            #sim.plot_boxplots(sim.operator_confidence, 'Operator confidence over time')
            #sim.plot_boxplots(sim.operator_internal_error, 'Operator belief map error over time')
            
            sim.save_positions(sim, directory)
            sim.save_boxplots(sim.swarm_confidence, 'confidence_time', directory)
            sim.save_boxplots(sim.swarm_internal_error, 'belief_error', directory)

            sim.save_boxplots(sim.operator_confidence, 'operator_confidence_time', directory)
            sim.save_boxplots(sim.operator_internal_error, 'operator_belief_error', directory)
            sim.save_boxplots(sim.operator_internal_error, 'operator_belief_error', directory)
            
            # Saving images of plots
            if not os.path.isdir(directory + '/map_images'):
                os.makedirs(directory + '/map_images')
            sim.save_image_plot_heatmaps(sim.operator_confidence_maps, 'operator confidence', directory)
            sim.save_image_plot_heatmaps(sim.operator_belief_maps, 'operator belief', directory)

            sim.save_image_plot_boxplots(sim.operator_confidence, 'operator_confidence_time', directory)
            sim.save_image_plot_boxplots(sim.operator_internal_error, 'operator_belief_error', directory)
            print('END')
            
        except KeyboardInterrupt:
            print("Arcade stopped on user request.")

def merge(list1, list2):       
    merged_list = [] 
    for i in range(max((len(list1), len(list2)))):   
        while True: 
            try: 
                tup = (list1[i], list2[i]) 
            except IndexError: 
                if len(list1) > len(list2): 
                    list2.append('') 
                    tup = (list1[i], list2[i]) 
                elif len(list1) < len(list2): 
                    list1.append('') 
                    tup = (list1[i], list2[i]) 
                continue  
            merged_list.append(tup) 
            break
    return merged_list 

if __name__ == '__main__':    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-size', type = int, default = 15) #swarm_size
    parser.add_argument('-name', type = str, default = "General") #experiment_name
    parser.add_argument('-d_size', type=int, default = 1)
    parser.add_argument('-d_xs', nargs='+', type=int, default = [500])
    parser.add_argument('-d_ys', nargs='+', type=int, default = [500])
    parser.add_argument('-d_move', type = bool, default = False)#moving disaster
    parser.add_argument('-op_size', type=int, default = 1)
    parser.add_argument('-op_xs', nargs='+', type=int, default = [450])
    parser.add_argument('-op_ys', nargs='+', type=int, default = [300])
    parser.add_argument('-noise', type = int, default = 0) #communication_noise
    parser.add_argument('-r_min', type = int, default = 100) #min_reliability
    parser.add_argument('-r_max', type = int, default = 100) #max_reliability
    parser.add_argument('-r_perc', type = int, default = 0) #unreliability_percentage
    parser.add_argument('-cmd', type = str, default = None) #normal_command
    parser.add_argument('-cmd_t', type = int, default = 0) #command_period
    parser.add_argument('-const_repel', type = bool, default = False) #constant_repulsion
    parser.add_argument('-alpha', type = float, default = 10) #command strength
    parser.add_argument('-comm_range', type = int, default = 4) #communication_range
    parser.add_argument('-vis_range', type = int, default = 2) #vision_range
    parser.add_argument('-w', type = float, default = 0.01) #velocity_weight_coef
    parser.add_argument('-bound', type = float, default = 1) #boundary_repulsion
    parser.add_argument('-aging', type = float, default = 0.9999) #boundary_repulsion
    parser.add_argument('-hum_r', type = int, default = 100)#operator_vision_radius    
    parser.add_argument('-height', type = int, default = 600) #arena_height
    parser.add_argument('-width', type = int, default = 600) #arena_width
    parser.add_argument('-grid_x', type = int, default = 40) #grid_x
    parser.add_argument('-grid_y', type = int, default = 40) #grid_y
    parser.add_argument('-input_time', type = int, default = 300) #input_time
    parser.add_argument('-gp', type = bool, default = False) #gaussian processes
    parser.add_argument('-gp_step', type = int, default = 50) #gaussian processes step
    parser.add_argument('-maze', type = str, default = None) #maze
    parser.add_argument('-walls', type = bool, default = False) #communication through walls
    parser.add_argument('-run_time', type = int, default = 1000) #communication through walls
    parser.add_argument('-communication_noise_strength', type = float, default = 0) 
    parser.add_argument('-communication_noise_prob', type = float, default = 0) # comm rate
    parser.add_argument('-positioning_noise_strength', type = float, default = 0) 
    parser.add_argument('-positioning_noise_prob', type = float, default = 0) 
    parser.add_argument('-sensing_noise_strength', type = float, default = 0) 
    parser.add_argument('-sensing_noise_prob', type = float, default = 0) 
    parser.add_argument('-exp_type', type = str, default = None) # Online experiment modes

    args = parser.parse_args()
    
    disasters_locations = merge(args.d_xs, args.d_ys)
    operators_locations = merge(args.op_xs, args.op_ys)
    
    if args.d_size > len(args.d_xs):
        disasters_locations += [('random', 'random')]*(args.d_size - len(args.d_xs))
        
    if args.op_size > len(args.op_xs):
        operators_locations += [('random', 'random')]*(args.op_size - len(args.op_xs))

    init(args.size, args.width, args.height, args.name, args.run_time, args.input_time, args.grid_x, args.grid_y, len(disasters_locations), 
         disasters_locations, len(operators_locations), operators_locations, (args.r_min, args.r_max), args.r_perc, args.noise, args.d_move, 
         args.alpha, args.cmd, args.cmd_t, args.const_repel, args.hum_r, args.comm_range, args.vis_range, args.w, args.bound, args.aging, 
         args.gp, args.gp_step, args.maze, args.walls, args.communication_noise_strength, args.communication_noise_prob,
         args.positioning_noise_strength, args.positioning_noise_prob, args.sensing_noise_strength, args.sensing_noise_prob, args.exp_type)