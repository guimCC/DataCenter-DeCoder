export interface IOField {
    is_input: boolean;
    is_output: boolean;
    unit: string;
    amount: number;
}
  
export interface Module {
    id: number;
    name: string;
    io_fields: IOField[];
} 

/* Afegeix més propietats al mòdul*/
export interface PositionedModule extends Module {
    gridColumn: number;
    gridRow: number;
  }
  