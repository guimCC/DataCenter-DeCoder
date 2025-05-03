export interface IOField {
    is_input: boolean;
    is_output: boolean;
    unit: string;
    amount: number;
}
  
export interface Module {
    id: string;
    name: string;
    io_fields: IOField[];
} 

/* Afegeix més propietats al mòdul*/
export interface PositionedModule extends Module {
    gridColumn: number;
    gridRow: number;
    height: number;
    width: number;
  }

  export interface SpecRule {
    Below_Amount: number;
    Above_Amount: number;
    Minimize: number;
    Maximize: number;
    Unconstrained: number;
    Unit: string;
    Amount: number;
  }
  
  // Update the DataCenter interface
  export interface DataCenter {
    id: number;
    name: string;
    specs: SpecRule[];  // Change from string to array of SpecRule
    details: Record<string, number>;
    modules: PositionedModule[];  // Change to match backend response
  }