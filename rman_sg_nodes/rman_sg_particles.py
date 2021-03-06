from .rman_sg_node import RmanSgNode

class RmanSgParticles(RmanSgNode):

    def __init__(self, rman_scene, sg_node, db_name):
        super().__init__(rman_scene, sg_node, db_name)
        self.matrix_world = None
        self.npoints = -1
        self.render_type = ''
        
        self.rman_sg_emitter = None
        self.rman_sg_hair = None
        self.particles_type = ''

    @property
    def matrix_world(self):
        return self.__matrix_world

    @matrix_world.setter
    def matrix_world(self, mtx):
        self.__matrix_world = mtx

    @property
    def npoints(self):
        return self.__npoints

    @npoints.setter
    def npoints(self, npoints):
        self.__npoints = npoints

    @property
    def render_type(self):
        return self.__render_type

    @render_type.setter
    def render_type(self, render_type):
        self.__render_type = render_type        

