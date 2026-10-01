"""
Farm AI - Job/Task assignment system for workers and vehicles.
Manages the autonomous behavior of the farm.
"""
import logging
import random
from typing import List, Optional

from src.entities.workers.worker import (
    Worker, WorkerState, TaskType, Profession, TASK_PRIORITY
)
from src.entities.vehicles.vehicle import (
    Vehicle, VehicleState, VehicleType, AttachmentType
)
from src.fields.field import Field, TileState

logger = logging.getLogger("farm_ai")


class FarmAI:
    """
    Manages automatic task assignment and worker/vehicle coordination.
    Uses a priority-based job system.
    """

    def __init__(self):
        self.task_cooldown = 0.0
        self.task_check_interval = 2.0  # Check every 2 seconds

    def update(self, dt: float, workers: List[Worker], vehicles: List[Vehicle],
               fields: List[Field], economy):
        """Main AI update - assign tasks to idle workers."""
        self.task_cooldown -= dt
        if self.task_cooldown > 0:
            return

        self.task_cooldown = self.task_check_interval

        # Find available workers
        available = [w for w in workers if w.is_available]
        if not available:
            return

        # Generate available tasks sorted by priority
        tasks = self._generate_tasks(fields, vehicles, economy)
        if not tasks:
            # Maybe send workers to rest or wander
            for w in available:
                if w.energy < 60:
                    w.state = WorkerState.RESTING
                    w.current_task = TaskType.REST
                elif random.random() < 0.1:
                    # Random wander
                    w.move_to(w.x + random.uniform(-80, 80))
            return

        # Sort tasks by priority
        tasks.sort(key=lambda t: TASK_PRIORITY.get(t['type'], 99))

        # Assign tasks
        for task in tasks:
            if not available:
                break

            # Find best worker for this task
            best = self._find_best_worker(available, task)
            if best:
                self._assign_task(best, task, vehicles, fields)
                available.remove(best)

    def _generate_tasks(self, fields: List[Field], vehicles: List[Vehicle],
                        economy) -> List[dict]:
        """Generate list of available tasks based on farm state."""
        tasks = []

        # Check vehicles needing repair
        for v in vehicles:
            if v.state == VehicleState.BROKEN:
                tasks.append({
                    'type': TaskType.REPAIR_VEHICLE,
                    'vehicle_id': v.id,
                    'x': v.x,
                    'priority': 1,
                })

        # Check vehicles needing fuel
        for v in vehicles:
            if v.needs_fuel and v.state != VehicleState.BROKEN:
                tasks.append({
                    'type': TaskType.REFUEL_VEHICLE,
                    'vehicle_id': v.id,
                    'x': v.x,
                    'priority': 8,
                })

        for field in fields:
            # Harvest ready fields
            if field.is_ready_for_harvest:
                tasks.append({
                    'type': TaskType.HARVEST_FIELD,
                    'field_id': field.field_id,
                    'x': field.x,
                    'priority': 2,
                })

            # Fields needing plowing (after harvest or initial)
            elif field.needs_plowing:
                tasks.append({
                    'type': TaskType.PLOW_FIELD,
                    'field_id': field.field_id,
                    'x': field.x,
                    'priority': 6,
                })

            # Fields needing seeding
            elif field.needs_seeding:
                tasks.append({
                    'type': TaskType.SEED_FIELD,
                    'field_id': field.field_id,
                    'x': field.x,
                    'priority': 4,
                })

            # Growing fields - inspection
            elif field.is_growing:
                if random.random() < 0.1:  # Don't over-inspect
                    tasks.append({
                        'type': TaskType.INSPECT_CROP,
                        'field_id': field.field_id,
                        'x': field.x + random.randint(0, field.width * 6),
                        'priority': 7,
                    })

        # Transport task if storage has crops
        if economy.storage.total_stored > 100 and economy.auto_sell != "never":
            tasks.append({
                'type': TaskType.TRANSPORT_CROP,
                'x': 100,  # Storage location
                'priority': 7,
            })

        return tasks

    def _find_best_worker(self, available: List[Worker], task: dict) -> Optional[Worker]:
        """Find the best available worker for a task."""
        task_type = task['type']

        # Score workers based on relevant skills
        scored = []
        for w in available:
            score = 0

            if task_type == TaskType.PLOW_FIELD:
                score = w.driving * 2 + w.level * 5
                if w.profession == Profession.TRACTOR_DRIVER:
                    score += 50

            elif task_type == TaskType.SEED_FIELD:
                score = w.driving + w.agronomy + w.level * 5
                if w.profession == Profession.TRACTOR_DRIVER:
                    score += 30

            elif task_type == TaskType.HARVEST_FIELD:
                score = w.harvesting * 2 + w.driving + w.level * 5
                if w.profession == Profession.COMBINE_OPERATOR:
                    score += 50

            elif task_type == TaskType.INSPECT_CROP:
                score = w.agronomy * 3 + w.level * 5
                if w.profession == Profession.AGRONOMIST:
                    score += 100

            elif task_type == TaskType.REPAIR_VEHICLE:
                score = w.repair * 3 + w.level * 5
                if w.profession == Profession.MECHANIC:
                    score += 100

            elif task_type == TaskType.TRANSPORT_CROP:
                score = w.driving * 2 + w.level * 3
                if w.profession == Profession.TRUCK_DRIVER:
                    score += 50

            elif task_type == TaskType.REFUEL_VEHICLE:
                score = 50 + w.level * 3

            else:
                score = w.level * 10

            # Distance penalty
            dist = abs(w.x - task.get('x', w.x))
            score -= dist * 0.1

            scored.append((w, score))

        if scored:
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0]
        return None

    def _assign_task(self, worker: Worker, task: dict,
                     vehicles: List[Vehicle], fields: List[Field]):
        """Assign a task to a worker."""
        task_type = task['type']
        worker.current_task = task_type

        if task_type in (TaskType.PLOW_FIELD, TaskType.CULTIVATE_FIELD,
                        TaskType.SEED_FIELD):
            # Need a tractor
            tractor = self._find_available_vehicle(vehicles,
                                                   [VehicleType.SMALL_TRACTOR, VehicleType.MEDIUM_TRACTOR])
            if tractor:
                worker.assigned_vehicle_id = tractor.id
                worker.assigned_field_id = task.get('field_id')
                tractor.driver_id = worker.id

                # Set attachment based on task
                if task_type == TaskType.PLOW_FIELD:
                    tractor.attachment = AttachmentType.PLOW
                elif task_type == TaskType.CULTIVATE_FIELD:
                    tractor.attachment = AttachmentType.CULTIVATOR
                elif task_type == TaskType.SEED_FIELD:
                    tractor.attachment = AttachmentType.SEEDER

                # Worker walks to tractor
                worker.move_to(tractor.x)
                worker.state = WorkerState.WALKING
                logger.info(f"Worker {worker.name} assigned: {task_type.name} "
                           f"with vehicle {tractor.id}")
            else:
                worker.current_task = TaskType.NONE
                worker.state = WorkerState.IDLE

        elif task_type == TaskType.HARVEST_FIELD:
            combine = self._find_available_vehicle(vehicles,
                                                    [VehicleType.SMALL_COMBINE])
            if combine:
                worker.assigned_vehicle_id = combine.id
                worker.assigned_field_id = task.get('field_id')
                combine.driver_id = worker.id
                worker.move_to(combine.x)
                worker.state = WorkerState.WALKING
                logger.info(f"Worker {worker.name} assigned: HARVEST with combine {combine.id}")
            else:
                worker.current_task = TaskType.NONE

        elif task_type == TaskType.INSPECT_CROP:
            worker.assigned_field_id = task.get('field_id')
            worker.move_to(task.get('x', worker.x))
            worker.state = WorkerState.WALKING
            logger.info(f"Worker {worker.name} inspecting field")

        elif task_type == TaskType.REPAIR_VEHICLE:
            worker.assigned_vehicle_id = task.get('vehicle_id')
            worker.move_to(task.get('x', worker.x))
            worker.state = WorkerState.WALKING
            logger.info(f"Worker {worker.name} going to repair vehicle {task.get('vehicle_id')}")

        elif task_type == TaskType.TRANSPORT_CROP:
            truck = self._find_available_vehicle(vehicles,
                                                  [VehicleType.FARM_TRUCK])
            if truck:
                worker.assigned_vehicle_id = truck.id
                truck.driver_id = worker.id
                worker.move_to(truck.x)
                worker.state = WorkerState.WALKING
                logger.info(f"Worker {worker.name} assigned: TRANSPORT with truck {truck.id}")
            else:
                worker.current_task = TaskType.NONE

        elif task_type == TaskType.REFUEL_VEHICLE:
            worker.assigned_vehicle_id = task.get('vehicle_id')
            worker.move_to(task.get('x', worker.x))
            worker.state = WorkerState.WALKING

    def _find_available_vehicle(self, vehicles: List[Vehicle],
                                 types: List[VehicleType]) -> Optional[Vehicle]:
        """Find an available vehicle of the specified types."""
        for v in vehicles:
            if (v.vehicle_type in types and
                    v.state in (VehicleState.PARKED, VehicleState.IDLE) and
                    v.driver_id is None and
                    v.state != VehicleState.BROKEN and
                    v.fuel > 5):
                return v
        return None
