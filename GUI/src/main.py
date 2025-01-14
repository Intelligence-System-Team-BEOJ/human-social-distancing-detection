from bird_view_transfo_functions import compute_perspective_transform,compute_point_perspective_transformation
from tf_model_object_detection import Model
from colors import bcolors
from tkinter import *
from tkinter.filedialog import askopenfile
from PIL import Image, ImageTk
import numpy as np
import itertools
import imutils
import time
import math
import glob
import yaml
import cv2
import os

COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)
BIG_CIRCLE = 60
SMALL_CIRCLE = 3


#Create Tkinter window
root = Tk()
root.title('Human Social Distancing Detection Application')

root.attributes('-fullscreen', True)

#Title
title = Label(root, text = "Welcome to Human Social Distancing Detection Application",font="Raleway 16 bold", fg="gold4")
title.grid(column=0, row=0, columnspan=2, pady=(15,5))

#Upload button
browse_text = StringVar()
browse_btn = Button(root, textvariable=browse_text, command=lambda:open_file(), font="Raleway", bg="#086cdc", fg="white", height=2, width=15)
browse_text.set("Upload")
browse_btn.grid(column=0, row=1, columnspan=2)

#Terminate Button
terminate_txt = StringVar()
terminate_btn = Button(root, text="Exit Application", command=lambda:termint(), font="Raleway", bg="#70747c", fg="white", height=2, width=15)
terminate_btn.grid(column=0, row=2, ipady=5, columnspan=2, pady=5)

#Percentage for file processing
percent = Label(root, text = "File Processing: 0", font="Raleway 12")
percent.grid(column=0, row=3, padx=(120,60))

#Text for violation rules
counterTxt = Label(root, text = 'Rules Violated(by individual): 0', font="Raleway 12")
counterTxt.grid(column=0, row=4, padx=(120,60), pady=(0,5))

#Text for BEV title
bevTxt = Label(root, text = "Bird's Eye View", font="Raleway 12 bold")
bevTxt.grid(column=1, row=4, padx=(0,120), pady=(0,5))

def open_file():
    browse_text.set("Uploading...")
    file = askopenfile(parent=root, mode="rb", title="Choose a file", filetype=[("Video/Image", ".jpeg .png .jpg .avi .mp4")])

    if file: 
           browse_text.set("Done Uploaded")
           main(file.name)

termination = False          
def termint():
    global termination
    termination=True
    root.destroy()

def get_human_box_detection(boxes,scores,classes,height,width):
	"""
	For each object detected, check if it is a human and if the confidence >> our threshold.
	Return 2 coordonates necessary to build the box.
	@ boxes : all our boxes coordinates
	@ scores : confidence score on how good the prediction is -> between 0 & 1
	@ classes : the class of the detected object ( 1 for human )
	@ height : of the image -> to get the real pixel value
	@ width : of the image -> to get the real pixel value
	"""
	array_boxes = list() # Create an empty list
	for i in range(boxes.shape[1]):
		# If the class of the detected object is 1 and the confidence of the prediction is > 0.6
		if int(classes[i]) == 1 and scores[i] > 0.75:
			# Multiply the X coordonnate by the height of the image and the Y coordonate by the width
			# To transform the box value into pixel coordonate values.
			box = [boxes[0,i,0],boxes[0,i,1],boxes[0,i,2],boxes[0,i,3]] * np.array([height, width, height, width])
			# Add the results converted to int
			array_boxes.append((int(box[0]),int(box[1]),int(box[2]),int(box[3])))
	return array_boxes


def get_centroids_and_groundpoints(array_boxes_detected):
	"""
	For every bounding box, compute the centroid and the point located on the bottom center of the box
	@ array_boxes_detected : list containing all our bounding boxes
	"""
	array_centroids,array_groundpoints = [],[] # Initialize empty centroid and ground point lists
	for index,box in enumerate(array_boxes_detected):
		# Draw the bounding box
		# c
		# Get the both important points
		centroid,ground_point = get_points_from_box(box)
		array_centroids.append(centroid)
		array_groundpoints.append(centroid)
	return array_centroids,array_groundpoints


def get_points_from_box(box):
	"""
	Get the center of the bounding and the point "on the ground"
	@ param = box : 2 points representing the bounding box
	@ return = centroid (x1,y1) and ground point (x2,y2)
	"""
	# Center of the box x = (x1+x2)/2 et y = (y1+y2)/2
	center_x = int(((box[1]+box[3])/2))
	center_y = int(((box[0]+box[2])/2))
	# Coordiniate on the point at the bottom center of the box
	center_y_ground = center_y + ((box[2] - box[0])/2)
	return (center_x,center_y),(center_x,int(center_y_ground))


def change_color_on_topview(pair, bird_view_img):
    #Draw red circles for the designated pair of points
    cv2.circle(bird_view_img, (pair[0][0],pair[0][1]), BIG_CIRCLE, COLOR_RED, 2)
    cv2.circle(bird_view_img, (pair[0][0],pair[0][1]), SMALL_CIRCLE, COLOR_RED, -1)
    cv2.circle(bird_view_img, (pair[1][0],pair[1][1]), BIG_CIRCLE, COLOR_RED, 2)
    cv2.circle(bird_view_img, (pair[1][0],pair[1][1]), SMALL_CIRCLE, COLOR_RED, -1)

def draw_rectangle(corner_points,frame):
	# Draw rectangle box over the delimitation area
	cv2.line(frame, (corner_points[0][0], corner_points[0][1]), (corner_points[1][0], corner_points[1][1]), COLOR_BLUE, thickness=1)
	cv2.line(frame, (corner_points[1][0], corner_points[1][1]), (corner_points[3][0], corner_points[3][1]), COLOR_BLUE, thickness=1)
	cv2.line(frame, (corner_points[0][0], corner_points[0][1]), (corner_points[2][0], corner_points[2][1]), COLOR_BLUE, thickness=1)
	cv2.line(frame, (corner_points[3][0], corner_points[3][1]), (corner_points[2][0], corner_points[2][1]), COLOR_BLUE, thickness=1)

def most_frequent_point(List):
    countr = 0
    most_frequent_pt = 0
      
    for current_point in List:
        curr_pt_frequency = List.count(current_point)
        if(curr_pt_frequency > countr):
            countr = curr_pt_frequency
            most_frequent_pt = current_point
  
    return most_frequent_pt

#Main function which will be called after a File is uploaded
def main(video_path):
    #########################################
    # Load the config for the top-down view #
    #########################################
    print(bcolors.WARNING +"[ Loading config file for the bird view transformation ] "+ bcolors.ENDC)
    with open("../conf/config_birdview.yml", "r") as ymlfile:
        cfg = yaml.load(ymlfile)
    width_og, height_og = 0,0
    corner_points = []
    for section in cfg:
        corner_points.append(cfg["image_parameters"]["p1"])
        corner_points.append(cfg["image_parameters"]["p2"])
        corner_points.append(cfg["image_parameters"]["p3"])
        corner_points.append(cfg["image_parameters"]["p4"])
        width_og = int(cfg["image_parameters"]["width_og"])
        height_og = int(cfg["image_parameters"]["height_og"])
        img_path = cfg["image_parameters"]["img_path"]
        size_frame = cfg["image_parameters"]["size_frame"]
    print(bcolors.OKGREEN +" Done : [ Config file loaded ] ..."+bcolors.ENDC )


    #########################################
    #		     Select the model 			#
    #########################################
    model_path = 'C:/Users/Alvin/Desktop/Year 3 Sem 1/Intelligent System/covid-social-distancing-detection-master/covid-social-distancing-detection-master/src/frozen_inference_graph.pb'
    print(bcolors.WARNING + " [ Loading the TENSORFLOW MODEL ... ]"+bcolors.ENDC)
    model = Model(model_path)
    print(bcolors.OKGREEN +"Done : [ Model loaded and initialized ] ..."+bcolors.ENDC)


    #############################################################
    #		    Minimal distance for social distancing			#
    #############################################################
    #distance_minimum = input("Prompt the size of the minimal distance between 2 pedestrians : ")
    #if distance_minimum == "":
    distance_minimum = "110"


    #########################################
    #     Compute transformation matrix		#
    #########################################
    # Compute  transformation matrix from the original frame
    matrix,imgOutput = compute_perspective_transform(corner_points,width_og,height_og,cv2.imread(img_path))
    height,width,_ = imgOutput.shape
    blank_image = np.zeros((height,width,3), np.uint8)
    height = blank_image.shape[0]
    width = blank_image.shape[1]
    dim = (width, height)
    
    ######################################################
    #########									 #########
    # 				START THE VIDEO STREAM               #
    #########									 #########
    ######################################################
    vs = cv2.VideoCapture(video_path)
    output_video_1,output_video_2 = None,None
    
    tp_x = []
    tp_y = []
    btm_x = []
    btm_y = []
    
    #To allow the smallest point to be selected
    tp_x.sort()
    tp_y.sort()
    btm_x.sort()
    btm_y.sort()
    
    # Loop until the end of the video stream
    while True:
        # Load the image of the ground and resize it to the correct size
        img = cv2.imread("../img/static_frame_from_video.jpg")
        bird_view_img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)

        # Load the frame
        (frame_exists, frame) = vs.read()
        
        #Calculate the video length by frame and generate the processing percentage
        #Calculate formula(current frame/total frames)
        percentage = round((int(vs.get(cv2.CAP_PROP_POS_FRAMES))/int(vs.get(cv2.CAP_PROP_FRAME_COUNT))) * 100,2)
        percent["text"] = "File Processing: "+str(percentage)+"%"
        percent["fg"] = "green4"
        
        # Test if it has reached the end of the video
        if not frame_exists:
            break
        else:
            # Resize the image to the correct size
            frame = imutils.resize(frame, width=int(size_frame))
            
            # Make the predictions for this frame
            (boxes, scores, classes) =  model.predict(frame)

            # Get the human detected in the frame and return the 2 points to build the bounding box
            array_boxes_detected = get_human_box_detection(boxes,scores[0].tolist(),classes[0].tolist(),frame.shape[0],frame.shape[1])

            # Both of our lists that will contain the centroïds coordonates and the ground points
            array_centroids,array_groundpoints = get_centroids_and_groundpoints(array_boxes_detected)

            # Use the transform matrix to get the transformed coordonates
            transformed_downoids = compute_point_perspective_transformation(matrix,array_groundpoints)

            # Show every point on the top view image
            for point in transformed_downoids:
                x,y = point
                cv2.circle(bird_view_img, (x,y), BIG_CIRCLE, COLOR_GREEN, 2)
                cv2.circle(bird_view_img, (x,y), SMALL_CIRCLE, COLOR_GREEN, -1)
                
            #---Reset violation counter for each frame---
            counter = 0
            #---Refresh list for each frame----
            violate_list= []
            
            # Check if 2 or more people have been detected (otherwise no need to detect)
            if len(transformed_downoids) >= 2:
                for index,downoid in enumerate(transformed_downoids):
                    if not (downoid[0] > width or downoid[0] < 0 or downoid[1] > height+200 or downoid[1] < 0 ):
                        cv2.rectangle(frame,(array_boxes_detected[index][1],array_boxes_detected[index][0]),(array_boxes_detected[index][3],array_boxes_detected[index][2]),COLOR_GREEN,2)
                
                # Iterate over every possible 2 by 2 between the points combinations
                list_indexes = list(itertools.combinations(range(len(transformed_downoids)), 2))
                for i,pair in enumerate(itertools.combinations(transformed_downoids, r=2)):
                    # Check if the distance between each combination of points is less than the minimum distance chosen
                    if math.sqrt( (pair[0][0] - pair[1][0])**2 + (pair[0][1] - pair[1][1])**2 ) < int(distance_minimum):
                        #Count the violated individual
                        if pair[0][0] and pair[0][1] not in violate_list:
                            violate_list.append(pair[0][0])
                            violate_list.append(pair[0][1])
                            counter +=1
                        if pair[1][0] and pair[1][1] not in violate_list:
                            violate_list.append(pair[1][0])
                            violate_list.append(pair[1][1]) 
                            counter+=1

                        # Change the colors of the points that are too close from each other to red
                        if not (pair[0][0] > width or pair[0][0] < 0 or pair[0][1] > height+200  or pair[0][1] < 0 or pair[1][0] > width or pair[1][0] < 0 or pair[1][1] > height+200  or pair[1][1] < 0):
                            change_color_on_topview(pair, bird_view_img)
                            # Get the equivalent indexes of these points in the original frame and change the color to red
                            index_pt1 = list_indexes[i][0]
                            index_pt2 = list_indexes[i][1]
                            
                            #To include the coordinates of violated person objects
                            tp_x.append(array_boxes_detected[index_pt1][1])
                            tp_y.append(array_boxes_detected[index_pt1][0])
                            btm_x.append(array_boxes_detected[index_pt2][3])
                            btm_y.append(array_boxes_detected[index_pt2][2])
                                
                            cv2.rectangle(frame,(array_boxes_detected[index_pt1][1],array_boxes_detected[index_pt1][0]),(array_boxes_detected[index_pt1][3],array_boxes_detected[index_pt1][2]),COLOR_RED,2)
                            cv2.rectangle(frame,(array_boxes_detected[index_pt2][1],array_boxes_detected[index_pt2][0]),(array_boxes_detected[index_pt2][3],array_boxes_detected[index_pt2][2]),COLOR_RED,2)
                            
                            #Draw the region bounding box(blue color) for violation history
                            #Draw the region when there is more than one coordinates inside the list
                            if len(tp_x) > 1 and len(tp_y) > 1 and len(btm_x) > 1 and len(btm_y) > 1:
                                cv2.rectangle(frame,(most_frequent_point(tp_x),most_frequent_point(tp_y)),(most_frequent_point(btm_x),most_frequent_point(btm_y)),COLOR_BLUE,5)
                            
        # Draw the green rectangle to delimitate the detection zone
        draw_rectangle(corner_points,frame)
        #Update counter text
        counterTxt["text"] = "Rules Violated(by individual): "+str(counter)
        #If violation occurs color red
        if counter == 0:
            counterTxt["fg"] = "grey1"
        else:
            counterTxt["fg"] = "red3"
        
        #Display both video in the realtime by frame 
        #Video
        img1 = Image.fromarray(frame)
        #Video Size
        img1 = img1.resize((600, 600), Image.ANTIALIAS)
        img1 = ImageTk.PhotoImage(img1)
        img_label1 = Label(image=img1)
        img_label1.image = img1
        #Video Alignment(CSS)
        img_label1.grid(column=0, row=5, padx=(120,60))
        
        #Bird Eye View
        img2 = Image.fromarray(bird_view_img)
        #Video Size
        img2 = img2.resize((600, 600), Image.ANTIALIAS)
        img2 = ImageTk.PhotoImage(img2)
        img_label2 = Label(image=img2)
        img_label2.image = img2
        #Video Alignment(CSS)
        img_label2.grid(column=1, row=5, padx=(0,120))
        
        key = cv2.waitKey(1) & 0xFF
        # Write the both outputs video to a local folders
        if output_video_1 is None and output_video_2 is None:
            fourcc1 = cv2.VideoWriter_fourcc(*"MJPG")
            #Generate the output video into output folder with 25 frames 
            output_video_1 = cv2.VideoWriter("../output/video.avi", fourcc1, 25,(frame.shape[1], frame.shape[0]), True)
            fourcc2 = cv2.VideoWriter_fourcc(*"MJPG")
            output_video_2 = cv2.VideoWriter("../output/bird_view.avi", fourcc2, 25,(bird_view_img.shape[1], bird_view_img.shape[0]), True)
        elif output_video_1 is not None and output_video_2 is not None:
            output_video_1.write(frame)
            output_video_2.write(bird_view_img)
            
        global termination
        # Break the loop when the video ends
        if int(vs.get(cv2.CAP_PROP_POS_FRAMES)) == int(vs.get(cv2.CAP_PROP_FRAME_COUNT)) or termination:
            break
            
        #To update on the Tkinter interface with latest changes
        root.update()
root.mainloop()
