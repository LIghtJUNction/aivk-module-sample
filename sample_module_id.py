try:
    from aivk.core import LKM
except ImportError:
    raise ImportError(" import error : aivk etc.")

import logging

logger = logging.getLogger("aivk.example_module")

class Entry(LKM):
    """
    Module ID : sample_module_id
    Module Name : module name
    Module Version : 0.0.0
    Module Author : LIghtJUNction
    Module License : MIT
    Module Description : sample

    pls implement the following methods:
    why don't implement the onLoad, onUnload, onInstall, onUninstall, onUpdate methods?
    BECAUSE:
    LKM has already implemented these methods, and they are will be called.

    请实现以下方法:
    为什么不实现 onLoad, onUnload, onInstall, onUninstall, onUpdate 方法?
    因为:
    LKM 基类已经实现了这些方法，并且它们将被调用。

    """
    @classmethod
    async def _onLoad(cls):
        logger.info("Hello, AIVK!")
        logger.info("Example module loaded!")
        logger.info("This is an example module for AIVK.")
        logger.info("You can implement your own module here.")
        logger.info("Please refer to the documentation for more information.")
        

    @classmethod
    async def _onUnload(cls):
        logger.info("Example module unloaded!")
        
    @classmethod
    async def _onInstall(cls):
        logger.info("Example module installed!")

    @classmethod
    async def _onUninstall(cls):
        logger.info("Example module uninstalled!")

    @classmethod
    async def _onUpdate(cls):
        logger.info("Example module updated!")


