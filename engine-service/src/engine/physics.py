from dataclasses import dataclass
import math


"""
Will be connected to the the UI. 
These values will depend on the bike chosen.
"""
@dataclass
class BikeParams:
    mass_kg: float
    cda: float
    crr: float
    drivetrain_eff: float = 0.97
    air_density: float = 1.225

@dataclass
class RiderState:
    speed_mps: float = 0.0 #output to the UI
    distance_m: float = 0.0 
    fatigue: float = 0.0
    power_w: float = 0.0 #input from the kickr

@dataclass
class CourseSegment:
    grade: float
    curvature_radius_m: float | None = None
    surface_multiplier: float = 1.0

class BikePhysicsSimulator:
    """
    This method calculates the total weight. 
    CREATE another class that takes user stats please
    """
    def __init__(self, bike: BikeParams, rider_mass_kg: float):
        self.bike = bike
        self.total_mass = bike.mass_kg + rider_mass_kg
   
   
    """
    This method calculates drag
    """
    def drag_force(self, v: float) -> float:
        return 0.5 * self.bike.air_density * self.bike.cda * v * v


    """
    This method calculates rolling resistance
    """
    def rolling_force(self, grade: float, surface_multiplier: float = 1.0) -> float:
        normal_force = self.total_mass * 9.81 * math.cos(math.atan(grade))
        return self.bike.crr * normal_force * surface_multiplier


    """
    This method calculates the gravitational force.
    Param: Grade. This will be taken from the map that will 
    store the hill grades omfg how do we do that
    """
    def grade_force(self, grade: float) -> float:
        return self.total_mass * 9.81 * math.sin(math.atan(grade))

    """
    Calculates acceleration
    """
    def solve_acceleration(self, power_w: float, v: float, grade: float, surface_multiplier: float = 1.0) -> float:
        v_eff = max(v, 0.5)
        p_mech = power_w * self.bike.drivetrain_eff
        f_drag = self.drag_force(v)
        f_roll = self.rolling_force(grade, surface_multiplier)
        f_grade = self.grade_force(grade)
        f_drive = p_mech / v_eff
        f_net = f_drive - (f_drag + f_roll + f_grade)
        return f_net / self.total_mass

    """
    This method calculates the speed and distance from the acceleration
    """
    def step(self, state: RiderState, segment: CourseSegment, dt: float) -> RiderState:
        a = self.solve_acceleration(state.power_w, state.speed_mps, segment.grade, segment.surface_multiplier)
        new_speed = max(0.0, state.speed_mps + a * dt) #calculates the speed of the next step
        new_distance = state.distance_m + new_speed * dt #updates the distance
        return RiderState(
            speed_mps=new_speed,
            distance_m=new_distance,
            fatigue=state.fatigue,
            power_w=state.power_w
        )

class TrainerController:
    def __init__(self):
        self.target_grade = 0.0
        self.mode = "SIM"

    """
    Sets the ERG to sim mode. ie so it comes back from here
    sus out with AN how this relates to blue tooth
    Maybe turn this into an ENUM bc i don't like how hardcoded it is tbh
    Lets the grade be passed
    """
    def set_grade(self, grade: float):
        self.target_grade = grade
        self.mode = "SIM"
        

    """
    This method sets the Kickr to erg mode
    sends the target power that they need to meet
    """
    def set_erg_power(self, watts: float):
        self.mode = "ERG"
      

class GameLoop:
    
    def __init__(self, sim: BikePhysicsSimulator, trainer: TrainerController):
        self.sim = sim
        self.trainer = trainer
        self.state = RiderState()

    def update(self, measured_power_w: float, segment: CourseSegment, dt: float):
        self.state.power_w = measured_power_w
        self.trainer.set_grade(segment.grade)
        self.state = self.sim.step(self.state, segment, dt)
        return self.state