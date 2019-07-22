from autoplan.labels import Labels


class GeneralRainfallLabels(Labels):
    CleanFirst = 0
    CleanInSC = 1
    SingleLoop = 2
    NoCleaning = 3
    CleanUpAfter = 4
    Unclear = 5

    @classmethod
    def from_string(cls, s):
        if hasattr(cls, s):
            return getattr(cls, s)
        else:
            raise Exception(f"Unknown label {s}")


class DetailedRainfallLabels(Labels):
    TNFirst = 0
    CleanInSC = 1
    AccumStyle = 2
    SumFirst = 3
    CountFirst = 4
    NegFirst = 5
    SentinelFirst = 6
    NoCleaning = 7
    CleanUpAfter = 8
    FarOff = 9
    Rec = 10

    @classmethod
    def from_string(cls, s):
        if hasattr(cls, s):
            return getattr(cls, s)
        elif s == 'T&NFirst':
            return cls.TNFirst
        elif s == 'CleanInS&C':
            return cls.CleanInSC
        else:
            raise Exception(f"Unknown label {s}")
