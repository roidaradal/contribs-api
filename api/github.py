from datetime import date 
from pydantic import BaseModel, model_serializer

class Contrib(BaseModel):
    count: int = 0
    level: int = 0

    @model_serializer
    def serialize_contrib(self) -> tuple[int, int]:
        return (self.count, self.level)

MonthContribs = dict[str, Contrib]      # day => Contrib 
DevContribs = dict[str, MonthContribs]  # dev => MonthContribs

async def get_devs_contributions(devs: list[str], input_date: date) -> DevContribs:
    dev_contribs: DevContribs = {}
    for dev in devs: 
        month_contribs: MonthContribs = {}
        for i in range(1, 32):
            key = '%.2d' % i 
            month_contribs[key] = Contrib(count = i, level = i)
        dev_contribs[dev] = month_contribs
    return dev_contribs
