import cv2
cap = cv2.VideoCapture(0)
print("Camera check:", cap.isOpened())
cap.release()