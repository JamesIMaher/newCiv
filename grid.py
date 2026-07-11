class Grid:
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    ROWS = 1 #Constant to access the row portion of the grid_size
    COLUMNS = 0 #Constant to access the column portion of the grid_size

    ######################################################################
    # Grid: Class that holds the base terrain for the map
    #
    # grid_size: How many cells should appear on the map. Tuple containing (rows, columns)
    # screen_width: Width of the screen in pixels
    # screen_height: Height of the screen in pixels
    # cell_width: Calculated value of the width of each cell based on screen width
    # cell_height: Calculated value of each cell based on screen height
    # grid_texture: Double list where each element is an RGB color to be drawn as a rectangle.
    #
    #######################################################################

    def __init__(self, screen_width, screen_height, grid_size):

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.grid_size = grid_size #Should be an array with the number of cells in the x and y direction, respectively.
        self.cell_width, self.cell_height = self._initialize_cell_size(screen_width, screen_height, grid_size) #Determine width and height of cells
        self._setup_grid()
 
    def _initialize_cell_size(self, screen_width, screen_height, grid_size):
            cell_width = screen_width // grid_size[0]
            cell_height = screen_height // grid_size[1]
            return cell_width, cell_height

    def _setup_grid(self):
        self.grid_texture = [[Grid.BLACK for _ in range(self.grid_size[1])] for _ in range(self.grid_size[0])]
        
        for row in range(self.grid_size[Grid.ROWS]):
            for column in range(self.grid_size[Grid.COLUMNS]):
                if row % 2 == 0: #Even rows start Black
                    if column % 2 == 1:
                        self.grid_texture[column][row] = Grid.WHITE
                else: #Odd rows start White
                    if column % 2 == 0:
                        self.grid_texture[column][row] = Grid.WHITE
    
    def draw_grid_terrain(self, screen):
        #initally just draw some rectangles so we know this works.
        for row in range(self.screen_height):
            for column in range(self.screen_width):
                pass

    
              
              