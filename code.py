import numpy as np                                       #To perform operations on image pixels
from PIL import Image, ImageDraw, ImageSequence, ImageTk #To process image
import tkinter as tk
from tkinter import filedialog

MAX_DEPTH = 8
DETAIL_THRESHOLD = 13
SIZE_MULT = 1

def average_colour(image):
    # To convert image to np array storing pixel colour
    image_arr = np.asarray(image)

    # To get average of whole image
    avg_color_per_row = np.average(image_arr, axis=0)
    avg_color = np.average(avg_color_per_row, axis=0) 


    return (int(avg_color[0]), int(avg_color[1]), int(avg_color[2]))

def weighted_average(hist):
    total = sum(hist)
    error = value = 0

    if total > 0:
        value = sum(i * x for i, x in enumerate(hist)) / total
        error = sum(x * (value - i) ** 2 for i, x in enumerate(hist)) / total
        error = error ** 0.5

    return error

def get_detail(hist):
    red_detail = weighted_average(hist[:256])
    green_detail = weighted_average(hist[256:512])
    blue_detail = weighted_average(hist[512:768])

    detail_intensity = red_detail * 0.2989 + green_detail * 0.5870 + blue_detail * 0.1140

    return detail_intensity

class Quadrant():
    def __init__(self, image, bbox, depth):
        self.bbox = bbox
        self.depth = depth
        self.children = None
        self.leaf = False

        # crop image to quadrant size
        image = image.crop(bbox)
        hist = image.histogram()

        self.detail = get_detail(hist)
        self.colour = average_colour(image)

    def split_quadrant(self, image):
        left, top, width, height = self.bbox

        # get the middle coords of bbox
        middle_x = left + (width - left) / 2
        middle_y = top + (height - top) / 2

        # split root quadrant into 4 new quadrants
        upper_left = Quadrant(image, (left, top, middle_x, middle_y), self.depth+1)
        upper_right = Quadrant(image, (middle_x, top, width, middle_y), self.depth+1)
        bottom_left = Quadrant(image, (left, middle_y, middle_x, height), self.depth+1)
        bottom_right = Quadrant(image, (middle_x, middle_y, width, height), self.depth+1)

        # add new quadrants to root children
        self.children = [upper_left, upper_right, bottom_left, bottom_right]

class QuadTree():
    def __init__(self, image):
        self.width, self.height = image.size 

        # keep track of max depth achieved by recursion
        self.max_depth = 0

        # start compression
        self.start(image)
    
    def start(self, image):
        # create initial root
        self.root = Quadrant(image, image.getbbox(), 0)
        
        # build quadtree
        self.build(self.root, image)

    def build(self, root, image):
        if root.depth >= MAX_DEPTH or root.detail <= DETAIL_THRESHOLD:
            if root.depth > self.max_depth:
                self.max_depth = root.depth

            # assign quadrant to leaf and stop recursing
            root.leaf = True
            return 
        
        # split quadrant if there is too much detail
        root.split_quadrant(image)

        for children in root.children:
            self.build(children, image)

    def create_image(self, custom_depth, show_lines=False):
        # create blank image canvas
        image = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, self.width, self.height), (0, 0, 0))

        leaf_quadrants = self.get_leaf_quadrants(custom_depth)

        # draw rectangle size of quadrant for each leaf quadrant
        for quadrant in leaf_quadrants:
            if show_lines:
                draw.rectangle(quadrant.bbox, quadrant.colour, outline=(0, 0, 0))
            else:
                draw.rectangle(quadrant.bbox, quadrant.colour)

        return image

    def get_leaf_quadrants(self, depth):
        if depth > self.max_depth:
            raise ValueError('A depth larger than the trees depth was given')

        quadrants = []

        # search recursively down the quadtree
        self.recursive_search(self, self.root, depth, quadrants.append)

        return quadrants

    def recursive_search(self, tree, quadrant, max_depth, append_leaf):
        # append if quadrant is a leaf
        if quadrant.leaf == True or quadrant.depth == max_depth:
            append_leaf(quadrant)

        # otherwise keep recursing
        elif quadrant.children != None:
            for child in quadrant.children:
                self.recursive_search(tree, child, max_depth, append_leaf)

    def create_gif(self, file_name, duration=1000, loop=0, show_lines=False):
        gif = []
        end_product_image = self.create_image(self.max_depth, show_lines=show_lines)

        for i in range(self.max_depth):
            image = self.create_image(i, show_lines=show_lines)
            gif.append(image)

        # add extra images at end
        for _ in range(4):
            gif.append(end_product_image)

        gif[0].save(
            file_name,
            save_all=True,
            append_images=gif[1:],
            duration=duration, loop=loop)

class GIFPlayer:
    def __init__(self, root, canvas_width, canvas_height, frame_width, frame_height):
        self.root = root
        self.root.title("GIF Player")

        self.gif_source = "GIF.gif"  # Specify the path to your GIF file
        self.gif_frames = []
        self.current_frame = 0
        self.delay = 1000  # Delay between frames in milliseconds

        # Adjust the canvas dimensions for the desired video display size
        self.canvas = tk.Canvas(self.root, width=canvas_width, height=canvas_height)
        self.canvas.pack()

        self.play_button = tk.Button(self.root, text="Play", command=self.play)
        self.stop_button = tk.Button(self.root, text="Stop", state=tk.DISABLED, command=self.stop)

        self.play_button.pack()
        self.stop_button.pack()

        # Adjust the frame dimensions for the desired frame size
        self.frame_width = frame_width
        self.frame_height = frame_height

    def load_gif_frames(self):
        self.gif_frames = []
        with Image.open(self.gif_source) as img:
            try:
                while True:
                    frame = img.resize((self.frame_width, self.frame_height), Image.ANTIALIAS)
                    self.gif_frames.append(ImageTk.PhotoImage(frame))
                    img.seek(img.tell() + 1)
            except EOFError:
                pass

    def play(self):
        if not self.gif_frames:
            self.load_gif_frames()
        self.play_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.play_frame()

    def play_frame(self):
        if self.current_frame < len(self.gif_frames):
            self.display_frame(self.gif_frames[self.current_frame])
            self.root.after(self.delay, self.play_frame)
            self.current_frame += 1
        else:
            self.current_frame = 0
            self.play_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def display_frame(self, frame):
        self.canvas.create_image(0, 0, anchor=tk.NW, image=frame)
        self.root.update()

    def stop(self):
        self.root.after_cancel(self.play_frame)
        self.play_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

def open_image_create():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")])
    
    if file_path:
        image = Image.open(file_path)
        image = image.resize((image.size[0] * SIZE_MULT, image.size[1] * SIZE_MULT))  
        # create quadtree
        quadtree = QuadTree(image)

        # create image with custom depth
        depth = 8
        image = quadtree.create_image(depth, show_lines=False)
        quadtree.create_gif("GIF.gif", show_lines=True)
        
        image.save("NEW.png")
def close_window():
    root.destroy() 
    
if __name__ == '__main__':
   
    # load image
    
    root = tk.Tk()
    root.title("Choose an Image")

    open_button = tk.Button(root, text="Open Image", command=open_image_create,width=20,height=8)
    f=("Century Gothics",15)
    open_button['font']=f
    open_button['border']=4
    open_button['bg'] = 'lightblue'
    open_button.pack()

    root.after(10000, close_window)
    root.mainloop()
    
    #Display the compressed image
    ni=Image.open("NEW.png")
    ni.show();

    root1 = tk.Tk()
    player = GIFPlayer(root1, canvas_width=800, canvas_height=600, frame_width=800, frame_height=600)
    root1.mainloop()    
      
      