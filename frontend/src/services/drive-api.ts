export interface DriveFolder {
  id: string
  name: string
  children?: DriveFolder[]
}

const dummyFolders: DriveFolder[] = [
  {
    id: "root",
    name: "My Drive",
    children: [
      {
        id: "finance",
        name: "Finance",
        children: [
          { id: "q1-reports", name: "Q1 Reports" },
          { id: "q2-reports", name: "Q2 Reports" },
          {
            id: "budgets",
            name: "Budgets",
            children: [
              { id: "team-budgets", name: "Team Budgets" },
              { id: "project-budgets", name: "Project Budgets" },
            ],
          },
        ],
      },
      {
        id: "marketing",
        name: "Marketing",
        children: [
          { id: "campaign-assets", name: "Campaign Assets" },
          { id: "brand-guidelines", name: "Brand Guidelines" },
        ],
      },
      {
        id: "personal",
        name: "Personal",
        children: [
          { id: "receipts", name: "Receipts" },
          { id: "travel", name: "Travel" },
        ],
      },
    ],
  },
]

export async function getDriveFolders(): Promise<DriveFolder[]> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(dummyFolders), 300)
  })
}
