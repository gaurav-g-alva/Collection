# generator.py
from deap import base, creator, tools, algorithms
import random
import numpy as np
from typing import List, Dict, Any
import models

class TimetableGenerator:
    def __init__(self, semester: int):
        self.semester = semester
        self.population_size = 100
        self.generations = 50
        self.mutation_rate = 0.1
        self.crossover_rate = 0.7
        
        # Initialize DEAP components
        creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMin)
        
        self.toolbox = base.Toolbox()
        self._setup_genetic_operators()
    
    def _setup_genetic_operators(self):
        # Initialize genetic operators
        self.toolbox.register("timeslot", random.randint, 0, 39)  # 8 periods * 5 days
        self.toolbox.register("individual", tools.initRepeat, creator.Individual,
                            self.toolbox.timeslot, n=len(self._get_courses()))
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        # Genetic operators
        self.toolbox.register("evaluate", self._evaluate_fitness)
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", tools.mutUniformInt, low=0, up=39, indpb=0.1)
        self.toolbox.register("select", tools.selTournament, tournsize=3)
    
    def _get_courses(self) -> List[Dict[str, Any]]:
        return [course for course in models.get_all_courses() 
                if course['semester'] == self.semester]
    
    def _get_faculty_availability(self) -> Dict[int, List[int]]:
        # Get faculty availability from database and convert to timeslot format
        faculty_schedules = {}
        cursor = models.db.conn.cursor()
        cursor.execute("SELECT faculty_id, day, start_time, end_time FROM faculty_availability")
        
        for faculty_id, day, start, end in cursor.fetchall():
            if faculty_id not in faculty_schedules:
                faculty_schedules[faculty_id] = []
            
            # Convert time to periods (assuming 1-hour periods)
            start_hour = int(start.split(':')[0]) - 8  # Assuming 8 AM start
            end_hour = int(end.split(':')[0]) - 8
            
            # Calculate timeslots
            day_offset = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].index(day) * 8
            faculty_schedules[faculty_id].extend(range(day_offset + start_hour, day_offset + end_hour))
        
        return faculty_schedules
    
    def _evaluate_fitness(self, individual) -> tuple:
        penalty = 0
        courses = self._get_courses()
        faculty_availability = self._get_faculty_availability()
        
        # Check for time slot conflicts
        used_slots = {}
        for i, timeslot in enumerate(individual):
            course = courses[i]
            faculty_id = course.get('faculty_id')
            
            # Faculty availability violation
            if faculty_id and faculty_id in faculty_availability:
                if timeslot not in faculty_availability[faculty_id]:
                    penalty += 100
            
            # Time slot collision
            if timeslot in used_slots:
                penalty += 100
            used_slots[timeslot] = course
            
            # Contiguous lab hours
            if course['type'] == 'Lab' and course['lab_hours'] > 1:
                if timeslot % 8 + course['lab_hours'] > 8:  # Check if lab spans across days
                    penalty += 50
        
        return (penalty,)
    
    def generate(self) -> List[Dict[str, Any]]:
        # Create initial population
        pop = self.toolbox.population(n=self.population_size)
        
        # Evolve population
        algorithms.eaSimple(pop, self.toolbox,
                          cxpb=self.crossover_rate,
                          mutpb=self.mutation_rate,
                          ngen=self.generations,
                          verbose=False)
        
        # Get best solution
        best_individual = tools.selBest(pop, 1)[0]
        
        # Convert solution to timetable format
        timetable = []
        courses = self._get_courses()
        
        for i, timeslot in enumerate(best_individual):
            course = courses[i]
            day = timeslot // 8
            period = timeslot % 8
            
            timetable.append({
                'course_code': course['code'],
                'course_name': course['name'],
                'faculty_id': course.get('faculty_id'),
                'day': ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][day],
                'period': period + 1,
                'type': course['type']
            })
        
        return timetable

def generate_timetable(semester: int) -> List[Dict[str, Any]]:
    generator = TimetableGenerator(semester)
    timetable = generator.generate()
    models.save_timetable(semester, timetable)
    return timetable