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