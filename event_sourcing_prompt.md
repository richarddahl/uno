# Event Sourcing Requirements

go through the uno.core.events pkg and review the code thoroughly.
Based on your analysis create a document named /EVENT_REQ.md
Create a specific action plan to refactor the code to create an event sourcing system.

The system should be:  
    - loosely coupled  
    - clean  
    - efficient  
    - modern python  
    - with type hints  
    - with unit tests  
    - with documentation  
    - with logging  

The system should be built with future extensibility for all aspects (loosely coupled)  

The system should integrate with the other systems in this codebase:  
    - ddd system in uno.core.domain  
    - central di system in uno.infrastructure.di  
    - central logging in uno.infrastructure.logging  
    - central error handling in uno.core.errors  
    - central configuration system in uno.infrastructure.config

The goal is to have a full featured event sourcing system  
The system will enable the library to create extremely performant, extensible, easily maintained modern python applications.  

Take your time and ensure your analysis is thorough.

review the code in uno/core/events and uno/core/domain. Document your findings in /DOMAIN_EVENTS.md SPecifically I want to know if the code in these two pkgs are a sound basis for a ddd based envent sourcing applicication development framework.  Ensure your analysis considers the following points: consistency with the code, integration of ddd and event sourcing.  Describe the changes that are necessary in order to get this library ready for use designing and deploying ddd event sourcing based applications,  Also look for orphaned or otherwise out of place code and provide a detailed refactoring plan that get restructure or otherwise modify this code appropriately.

this repository is uno.  A modern python library for ddd based event sourced application development.  It has an error handling mechanism (monad style) in uno.core.errors, a di system in uno.infrastructure.di, a config system in uno.infrastructure.config, the domain driven design and event sourcing defined in uno.core.domain and uno.core.events, centralized logging in uno.infrastructure.logging, and services in uno.core.services.  Review the codebase.  There is currenlty much missing, including: incomplete infrastructure and application integration.  Document your finding ins LIB_STATUS.md, focus on DRYness, modern python idioms, performance, ease of use.  THe documentation that exists may or may not be accurate, so ignore that for now, but list compprehensive documentation as a todo.  Let me know what you think of this library and any critical issues that must be resolved before those layers i mentioned earlier (domain, events, errors, logging, config, di, etc...) are ready to be used.  Be thorough in your analysis. think very hard.
