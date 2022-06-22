import os
import re
import sqlite3

from loguru import logger

ESE_FILE_PATH = "/uk.ese"
# get working directory
WORK_DIR = os.path.dirname(__file__)
logger.debug(WORK_DIR)

class SqLite:
    """Sqlite3 class for doing stuff"""
    def __init__(self) -> None:
        self.con = sqlite3.connect("/var/www/vccs.vnpas.uk/vccs/db.sqlite3")
        self.cur = self.con.cursor()
        self.table = "panel_controllerpositions"
    
    def select(self, criteria=False, where=False, order_by=False):
        """Run a SELECT query"""
        if not criteria:
            criteria = "*"
        
        if not order_by:
            order_by = ""
        else:
            order_by = f" ORDER BY {order_by} "
        
        if not where:
            where = ""
        else:
            where = f" WHERE {where} "

        query = f"SELECT {criteria} FROM {self.table}{where}{order_by}"
        logger.trace(query)

        return self.cur.execute(str(query).strip())
    
    def insert(self, values:list):
        """Run an INSERT query"""
        query_values = ""
        for value in values:
            if query_values == "":
                query_values = f"'{value}'"
            else:
                query_values = f"{query_values}, '{value}'"

        query = f"INSERT INTO {self.table} VALUES ({query_values})"
        logger.trace(query)
        
        self.cur.execute(str(query))
        self.con.commit()
    
    def delete_duplicates(self):
        """Runs a DELETE query"""
        query = f"DELETE FROM {self.table} WHERE EXISTS(SELECT 1 FROM {self.table} p2 WHERE {self.table}.name_of_position = p2.name_of_position AND {self.table}.id > p2.id)"
        logger.debug(query)
        self.cur.execute(str(query))
        self.con.commit()

def load_ese():
    # load sqlite3 db
    sq_db = SqLite()
    # count the rows
    rows = sq_db.select(criteria="id", order_by="id DESC")
    start_from = rows.fetchone()
    if start_from is None:
        start_from = 0
    else:
        start_from = int(start_from[0])

    process_file = True
    process_line = False
    with open(WORK_DIR + ESE_FILE_PATH, "r", encoding="utf-8") as file:
        while process_file:
            for line in file:
                # check to see if in the correct section
                section_name = re.search(r"\[([A-Za-z]{2,})\]", line)
                if section_name is not None:
                    if section_name.group(1) == "POSITIONS":
                        logger.info("Processing on")
                        process_line = True
                    else:
                        logger.info("Processing off")
                        process_line = False
                        process_file = False           
                elif process_line:
                    """
                    https://www.euroscope.hu/wp/ese-files-description/
                    0 = <name of position>
                    1 = <radio callsign>
                    2 = <frequency>
                    3 = <identifier>
                    4 = <middle letter>
                    5 = <prefix>
                    6 = <suffix>
                    7 onwards not used in this context
                    """
                    if not re.match(r'^;', line):
                        # split the line
                        split_line = line.split(":")

                        # check to see if there is already a DB entry
                        w_clause = f"name_of_position = '{split_line[0]}'"
                        db_check = sq_db.select(where=str(w_clause))
                        logger.trace(db_check.fetchone())
                        start_from += 1
                        if (db_check.fetchone() is None) and (len(split_line) > 7):
                            sq_db.insert([
                                start_from,
                                split_line[0],
                                split_line[1].replace("'", ""),
                                split_line[2],
                                split_line[3],
                                split_line[4],
                                split_line[5],
                                split_line[6],
                            ])
                        else:
                            logger.trace("Already exists. Skipping...")
    sq_db.delete_duplicates()

load_ese()