Please continue the prompt. You have yet to include the logic for lines in index.html. 
Also not implemented is the symbol palette for start and endpoint symbols

While you're at it, also fix it up and refactor the index.html file by separating the styling logic from the html. Also opt to separate the scripting logic 

Furthermore, ghosts still disappear when: adding cells (works), and then removing some cells or adding a symbol. Suddenly going back to adding cells causes the ghost cells to disappear. This seems to be remedied by clearing all values but I don't want to have to rely on this.


===============

Next lext augment the solver. Support a solver that will specialize in the line drawing puzzles. Furthermore, make that the default control scheme. Thus, players in play mode should, by default, be able to draw lines as specified (again same for the solver)