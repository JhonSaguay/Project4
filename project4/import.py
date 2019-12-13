import csv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session,sessionmaker
engine=create_engine(os.getenv("DATABASE_URL"))
db=scoped_session(sessionmaker(bind=engine))

def main():
    i=0
    f=open("LAST23.csv","r")
    reader=csv.reader(f)
    next(reader)
    for codigo,producto,precio,categoria in reader:
        db.execute("INSERT INTO productos(codigo,producto,precio,categoria) VALUES (:codigo,:producto,:precio,:categoria)",
        {"codigo":codigo,"producto":producto,"precio":precio,"categoria":categoria})
        db.commit()
if __name__=='__main__':
    main()
