import scipy as sp
import numpy as np
import pdb


from scipy.optimize import minimize

class Robot():
    def __init__(self,dim,goal,A,B,rho,K,index,H,M_part,col):
        self.A = A
        self.B = B
        self.dim=dim
        self.bdim = self.B.shape[0]
        # self.M = np.zeros((H*dim,(H)))
        self.goal =goal
        self.K = K
        self.index = index
        self.H = H
        self.safety =.5
        self.traj=[]
        # self.u0= np.vstack((np.ones((self.dim,1)),
        #                    np.zeros((self.H-1,1))))
        # self.u0 = np.ones((self.H,1))
        self.u0 = np.float64(np.random.randint(-2,5,size=(self.H,1)))
        self.control=[]
        self.u = np.zeros_like(self.u0)
        self.u_prev = np.zeros_like(self.u)
        self.lambd= np.zeros_like(self.u)
        self.rho = rho
        self.init_M(col, M_part)
        self.x0=self.col[:2,[self.index]]
        self.neighbors = None
        self.neighbors_dict={}
        self.eps = 10 #termination criteria
        self.W = np.zeros((self.dim,(self.H-1)*self.dim))
        self.W = np.hstack((self.W,np.eye(2))) #x' = Wx propagation matrix

    def init_M(self, col, M_part):
        # self.init = col[:2,[self.index]]
        self.inits = []
        for i in range(self.K):
            self.inits.append(col[:,self.dim*i:self.dim*(i+1)])
        self.col = col
        self.M = M_part[2:,:]

    def get_neighbors(self):
        # return np.mod([self.index-1+self.K,self.index+1],self.K)
        neigh = np.linspace(0,self.K-1,self.K,dtype=np.int32)
        return list(np.hstack((neigh[:self.index],neigh[self.index+1:])))

    def send_info(self):
        return [self.u, self.M]

    def augmented_lagrangian(self,u, u_prev ):
        neighbors = self.get_neighbors()

        x_aug = np.tile(self.x0,(self.H,1))
        mycol = self.col[:,[self.index]]
        init_aug=np.multiply(x_aug, mycol) #initial position propagated through time
        # cost=0.5 * np.linalg.norm(self.W@(np.expand_dims(self.M@u,axis=1) + init_aug)\
        #                                 -self.goal,2 )**2
        cost=0.5 * np.linalg.norm(self.W@np.expand_dims(self.M@u,axis=1)-self.goal,2 )**2
        regularization= 0
        for j in self.neighbors_dict.keys():
            # collision_avoidance = 0
            uj, Mj = self.neighbors_dict[j]
            distance = np.expand_dims(self.M@u,axis=1) +self.col[:,[self.index]]\
                        - Mj@uj-self.col[:,[j]] # 2Tx1 matrix
            # pdb.set_trace()
            for t in range(self.H):
                # pdb.set_trace()
                dist = np.linalg.norm(distance[self.dim*t:self.dim*(t+1)],2)**2
                # collision_avoidance += self.lambd[t,0]*(self.safety**2-dist)
            regularization += np.linalg.norm(u-(u_prev+uj)/2.0,2)**2
            # cost +=collision_avoidance
        cost+= self.rho*regularization

        return cost

    def primal_update(self,method='Powell'):
        result = sp.optimize.minimize(self.augmented_lagrangian,
                                    x0=self.u0,
                                    args=(self.u_prev),
                                    method=method)#,
        self.cost=result['fun']
        print(self.cost)
        # pdb.set_trace()
        self.u_prev = self.u
        self.u = np.expand_dims(result['x'],axis=1)

    def dual_update(self):
        new_lambd=self.lambd
        for j in self.neighbors_dict.keys():
            new_lambd +=  self.rho*( self.u - self.neighbors_dict[j][0])
        self.lambd_prev = self.lambd
        self.lambd = new_lambd

    def compare_vals(self):

        deviation = 0
        for j in self.neighbors_dict.keys():
            deviation += np.linalg.norm(self.u - self.neighbors_dict[j][0])
        if deviation< self.eps: #uj
            return True
        else :
            return False
