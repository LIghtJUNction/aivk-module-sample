try:
    from aivk.core import LKM
except ImportError:
    raise ImportError(" import error : aivk etc.")

class Entry(LKM):
    """
    Module ID
    """
    @staticmethod
    async def onLoad():
        pass
    @staticmethod
    async def onUnload():
        pass
    @staticmethod
    async def onInstall():
        pass
    @staticmethod
    async def onUninstall():
        pass
    @staticmethod
    async def onUpdate():
        pass

