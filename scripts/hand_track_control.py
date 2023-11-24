"""
Hand Tracking Module

Website: https://www.computervision.zone/
"""

import math

import cv2
import mediapipe as mp

import time


class HandDetector:
    """
    Finds Hands using the mediapipe library. Exports the landmarks
    in pixel format. Adds extra functionalities like finding how
    many fingers are up or the distance between two fingers. Also
    provides bounding box info of the hand found.
    """

    def __init__(self, staticMode=False, maxHands=2, modelComplexity=1, detectionCon=0.5, minTrackCon=0.5):

        """
        :param mode: In static mode, detection is done on each image: slower
        :param maxHands: Maximum number of hands to detect
        :param modelComplexity: Complexity of the hand landmark model: 0 or 1.
        :param detectionCon: Minimum Detection Confidence Threshold
        :param minTrackCon: Minimum Tracking Confidence Threshold
        """
        self.staticMode = staticMode
        self.maxHands = maxHands
        self.modelComplexity = modelComplexity
        self.detectionCon = detectionCon
        self.minTrackCon = minTrackCon
        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(static_image_mode=self.staticMode,
                                        max_num_hands=self.maxHands,
                                        model_complexity=modelComplexity,
                                        min_detection_confidence=self.detectionCon,
                                        min_tracking_confidence=self.minTrackCon)

        self.mpDraw = mp.solutions.drawing_utils
        self.tipIds = [4, 8, 12, 16, 20]
        self.fingers = []
        self.lmList = []

    def findHands(self, img, draw=True, flipType=True):
        """
        Finds hands in a BGR image.
        :param img: Image to find the hands in.
        :param draw: Flag to draw the output on the image.
        :return: Image with or without drawings
        """
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)
        allHands = []
        h, w, c = img.shape
        if self.results.multi_hand_landmarks:
            for handType, handLms in zip(self.results.multi_handedness, self.results.multi_hand_landmarks):
                myHand = {}
                ## lmList
                mylmList = []
                xList = []
                yList = []
                for id, lm in enumerate(handLms.landmark):
                    px, py, pz = int(lm.x * w), int(lm.y * h), int(lm.z * w)
                    mylmList.append([px, py, pz])
                    xList.append(px)
                    yList.append(py)

                ## bbox
                xmin, xmax = min(xList), max(xList)
                ymin, ymax = min(yList), max(yList)
                boxW, boxH = xmax - xmin, ymax - ymin
                bbox = xmin, ymin, boxW, boxH
                cx, cy = bbox[0] + (bbox[2] // 2), \
                         bbox[1] + (bbox[3] // 2)

                myHand["lmList"] = mylmList
                myHand["bbox"] = bbox
                myHand["center"] = (cx, cy)

                if flipType:
                    if handType.classification[0].label == "Right":
                        myHand["type"] = "Left"
                    else:
                        myHand["type"] = "Right"
                else:
                    myHand["type"] = handType.classification[0].label

                wristPoistion = mylmList[0]
                middleMCP = mylmList[9]

                vector = [wristPoistion[0] - middleMCP[0], wristPoistion[1] - middleMCP[1]]
                angle = math.atan2(vector[0], vector[1])

                myHand["angle"]= math.degrees(angle) % 360

                thumbPosition = mylmList[1]
                pinkyPosition = mylmList[17]

                # Determine the hand orientation based on the hand type.
                if myHand["type"] == "Right":
                    if thumbPosition[0] > pinkyPosition[0]:
                        handOrientation = "Front"
                    else:
                        handOrientation = "Back"
                else:
                    if thumbPosition[0] < pinkyPosition[0]:
                        handOrientation = "Front"
                    else:
                        handOrientation = "Back"

                # Flip hand orientation if the angle is between 80 and 260 degrees
                if 80 < myHand["angle"] < 260:
                    if handOrientation == "Front":
                        handOrientation = "Back"
                    elif handOrientation == "Back":
                        handOrientation = "Front"

                myHand["orientation"] = handOrientation

                allHands.append(myHand)

                ## draw
                if draw:
                    self.mpDraw.draw_landmarks(img, handLms,
                                               self.mpHands.HAND_CONNECTIONS)
                    cv2.rectangle(img, (bbox[0] - 20, bbox[1] - 20),
                                  (bbox[0] + bbox[2] + 20, bbox[1] + bbox[3] + 20),
                                  (255, 0, 255), 2)
                    cv2.putText(img, myHand["type"], (bbox[0] - 30, bbox[1] - 30), cv2.FONT_HERSHEY_PLAIN,
                                2, (255, 0, 255), 2)

        return allHands, img

    def fingersUp(self, myHand):
        """
        Finds how many fingers are open and returns in a list.
        Considers left and right hands separately
        :return: List of which fingers are up
        """
        fingers = []
        myHandType = myHand["type"]
        myLmList = myHand["lmList"]
        myOrientation = myHand["orientation"]
        if self.results.multi_hand_landmarks:
            # Thumb
            if myHandType == "Right":
                fingerUp = myLmList[self.tipIds[0]][0] > myLmList[self.tipIds[0] - 1][0]
            else:
                fingerUp = myLmList[self.tipIds[0]][0] < myLmList[self.tipIds[0] - 1][0]

            if myOrientation == "Back":
                fingerUp = not fingerUp

            if 80 < myHand["angle"] < 260:
                fingerUp = not fingerUp

            fingers.append(1 if fingerUp else 0)

            # 4 Fingers
            for id in range(1, 5):
                if myLmList[self.tipIds[id]][1] < myLmList[self.tipIds[id] - 2][1]:
                    if 80 < myHand["angle"] < 260:
                        fingers.append(0)
                    else:
                        fingers.append(1)
                else:
                    if 80 < myHand["angle"] < 260:
                        fingers.append(1)
                    else:
                        fingers.append(0)
        return fingers

    def findDistance(self, p1, p2, img=None, color=(255, 0, 255), scale=5):
        """
        Find the distance between two landmarks input should be (x1,y1) (x2,y2)
        :param p1: Point1 (x1,y1)
        :param p2: Point2 (x2,y2)
        :param img: Image to draw output on. If no image input output img is None
        :return: Distance between the points
                 Image with output drawn
                 Line information
        """

        x1, y1 = p1
        x2, y2 = p2
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        length = math.hypot(x2 - x1, y2 - y1)
        info = (x1, y1, x2, y2, cx, cy)
        if img is not None:
            cv2.circle(img, (x1, y1), scale, color, cv2.FILLED)
            cv2.circle(img, (x2, y2), scale, color, cv2.FILLED)
            cv2.line(img, (x1, y1), (x2, y2), color, max(1, scale // 3))
            cv2.circle(img, (cx, cy), scale, color, cv2.FILLED)

        return length, info, img


def start_camera_and_read_hand():
    gesture_start_time = None
    last_gesture = None
    capturing = True

    # Initialize the webcam to capture video
    cap = cv2.VideoCapture(0)

    # Initialize the HandDetector class with the given parameters
    detector = HandDetector(staticMode=False, maxHands=1, modelComplexity=1, detectionCon=0.5, minTrackCon=0.5)

    while capturing:
        success, img = cap.read()
        hands, img = detector.findHands(img, draw=True, flipType=True)

        if hands:



def main():

    gesture1StartTime = None
    lastGesture1 = None

    # Initialize the webcam to capture video
    # The '2' indicates the third camera connected to your computer; '0' would usually refer to the built-in camera
    cap = cv2.VideoCapture(0)

    # Initialize the HandDetector class with the given parameters
    detector = HandDetector(staticMode=False, maxHands=1, modelComplexity=1, detectionCon=0.5, minTrackCon=0.5)

    # Continuously get frames from the webcam
    while True:
        # Capture each frame from the webcam
        # 'success' will be True if the frame is successfully captured, 'img' will contain the frame
        success, img = cap.read()

        # Find hands in the current frame
        # The 'draw' parameter draws landmarks and hand outlines on the image if set to True
        # The 'flipType' parameter flips the image, making it easier for some detections
        hands, img = detector.findHands(img, draw=True, flipType=True)

        # Check if any hands are detected
        if hands:
            # Information for the first hand detected
            hand1 = hands[0]  # Get the first hand detected
            lmList1 = hand1["lmList"]  # List of 21 landmarks for the first hand

            fingers1 = detector.fingersUp(hand1)
            totalFingers1 = fingers1.count(1)
            stopCamera = False

            if totalFingers1 == lastGesture1:
                if gesture1StartTime is None:
                    gesture1StartTime = time.time()
                else:
                    # Print the countdown
                    countdown1 = 3 - int(time.time() - gesture1StartTime)
                    print(f"Hand = {totalFingers1}, countdown: {countdown1}", end=" ")
                    cv2.putText(img, str(countdown1), (10,70), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 5)
                    if time.time() - gesture1StartTime >= 3:
                        print(f"\nHand 1 Going to: {'table ' + str(totalFingers1) if totalFingers1 != 0 else 'Till'}", end=" ")
                        cv2.putText(img, "table " +str(totalFingers1) if totalFingers1 != 0 else "Till", (45, 375),
                                    cv2.FONT_HERSHEY_PLAIN, 10, (255, 0, 0), 25)

                        gesture1StartTime = None  # Reset the start time
                        confirmationStartTime = time.time() # Start the text display timer

                        # Display the image with the text for one second
                        while time.time() - confirmationStartTime < 1:
                            cv2.imshow("Image", img)
                            if cv2.waitKey(1) & 0xFF == ord('q'):  # Add a way to break the loop if needed
                                break

                            stopCamera = True

            else:
                lastGesture1 = totalFingers1
                gesture1StartTime = time.time()  # Start the countdown

            if stopCamera:
                cap.release()
                cv2.destroyAllWindows()
                return

            # Calculate distance between specific landmarks on the first hand and draw it on the image
            length, info, img = detector.findDistance(lmList1[8][0:2], lmList1[12][0:2], img, color=(255, 0, 255),
                                                      scale=10)

            print(" ")  # New line for better readability of the printed output

        # Display the image in a window
        cv2.imshow("Image", img)

        # Keep the window open and update it for each frame; wait for 1 millisecond between frames
        cv2.waitKey(1)


if __name__ == "__main__":
    main()